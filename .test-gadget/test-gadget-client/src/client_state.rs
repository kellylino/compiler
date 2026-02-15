use std::{fmt::Display, fs, io, io::Write, path::PathBuf, str::FromStr};

use serde::Deserialize;
use serde_json::json;
use thiserror::Error;

use crate::requests::create_reqwest_client;

const DEFAULT_DIR: &str = ".test-gadget";

pub struct ClientState {
    pub course_config: CourseConfig,
    pub auth_token: String,

    pub temp_container_file: PathBuf,
    pub temp_container_diff_file: PathBuf,
    pub last_submission_id_file: PathBuf,
    pub last_submission_rsync_signature_file: PathBuf,
    pub last_submission_container_file: PathBuf, // Usually not stored
}

// This should include non-user-specific configs that aren't gitignored.
#[derive(Deserialize, Default)]
pub struct CourseConfig {
    pub server_base_url: Option<String>,
}

#[derive(Error, Debug)]
pub enum ClientStateError {
    MissingDirectory,
    MissingServerBaseUrl,
    LoginFailed(reqwest::Error),
    LoginResponseParseFailed(serde_json::Error),
    MissingSecretToken(PathBuf),
    FailedToInit(io::Error),
    FailedToReadConfigFile(PathBuf, io::Error),
    FailedToParseConfigFile(PathBuf, serde_json::Error),
    FailedToReadSecretToken(PathBuf, io::Error),
}

impl CourseConfig {
    pub fn load() -> Result<CourseConfig, ClientStateError> {
        let dir = ClientState::dir();
        if !dir.exists() {
            return Err(ClientStateError::MissingDirectory);
        }
        let course_config_path = dir.join("course.json");
        let course_config: CourseConfig = if course_config_path.exists() {
            let config_str = fs::read_to_string(&course_config_path)
                .map_err(|e| {
                    ClientStateError::FailedToReadConfigFile(course_config_path.clone(), e)
                })?
                .trim()
                .to_string();
            serde_json::de::from_str(&config_str)
                .map_err(|e| ClientStateError::FailedToParseConfigFile(course_config_path, e))?
        } else {
            CourseConfig::default()
        };
        Ok(course_config)
    }

    pub fn get_server_baseurl(&self, server_baseurl_override: Option<&str>) -> Option<String> {
        let baseurl_opt =
            server_baseurl_override.or(self.server_base_url.as_ref().map(|s| s.as_str()));
        baseurl_opt.map(|s| s.to_string())
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct LoginResponse {
    result: LoginResponseResult,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct LoginResponseResult {
    data: LoginResponseData,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct LoginResponseData {
    token: String,
}

impl ClientState {
    pub fn prompt_for_login_and_init(
        server_baseurl_override: Option<&str>,
    ) -> Result<ClientState, ClientStateError> {
        let dir = Self::dir();
        if !dir.exists() {
            fs::create_dir_all(&dir).map_err(|e| ClientStateError::FailedToInit(e))?;
        }

        let course_config = CourseConfig::load()?;

        let mut server_baseurl = course_config
            .get_server_baseurl(server_baseurl_override)
            .ok_or(ClientStateError::MissingServerBaseUrl)?;
        while server_baseurl.ends_with('/') {
            server_baseurl.pop();
        }

        let auth_token_file = dir.join("auth_token");
        let auth_token: String = if atty::is(atty::Stream::Stdin) {
            println!(
                "Login needed. Create an account at {}/signup if you don't have one yet.",
                server_baseurl
            );

            loop {
                print!("Username > ");
                io::stdout()
                    .flush()
                    .map_err(|e| ClientStateError::FailedToInit(e))?;
                let mut input = String::new();
                io::stdin()
                    .read_line(&mut input)
                    .map_err(|e| ClientStateError::FailedToInit(e))?;
                let username = input.trim().to_string();

                let password = rpassword::prompt_password("Password > ")
                    .map_err(|e| ClientStateError::FailedToInit(e))?;

                println!("Logging in...");

                let server_url = format!("{}/api/logIn", server_baseurl);
                let client =
                    create_reqwest_client().map_err(|e| ClientStateError::LoginFailed(e))?;
                let response = client
                    .post(server_url)
                    .json(&json!({
                        "username": username,
                        "password": password,
                    }))
                    .send()
                    .map_err(|e| ClientStateError::LoginFailed(e))?
                    .error_for_status();

                if let Err(e) = response.as_ref() {
                    if let Some(status) = e.status() {
                        if status.as_u16() == 403 {
                            println!("Incorrect username or password.");
                            continue;
                        }
                    }
                }

                let response = response.map_err(|e| ClientStateError::LoginFailed(e))?;
                let response_json: serde_json::Value = response
                    .json()
                    .map_err(|e| ClientStateError::LoginFailed(e))?;
                let result: LoginResponse = serde_json::from_value(response_json)
                    .map_err(|e| ClientStateError::LoginResponseParseFailed(e))?;
                break result.result.data.token;
            }
        } else {
            return Err(ClientStateError::FailedToInit(io::Error::new(
                io::ErrorKind::Other,
                "Not prompting for login due to not being in a TTY.",
            )));
        };
        fs::write(&auth_token_file, auth_token).map_err(|e| ClientStateError::FailedToInit(e))?;
        println!("Cookie saved to {}", auth_token_file.display());

        Self::load()
    }

    pub fn load() -> Result<ClientState, ClientStateError> {
        let dir = Self::dir();
        if !dir.exists() {
            return Err(ClientStateError::MissingDirectory);
        }
        let course_config = CourseConfig::load()?;
        let auth_token_file = dir.join("auth_token");
        if !auth_token_file.exists() {
            return Err(ClientStateError::MissingSecretToken(auth_token_file));
        }
        let auth_token = fs::read_to_string(&auth_token_file)
            .map_err(|e| ClientStateError::FailedToReadSecretToken(auth_token_file, e))?
            .trim()
            .to_string();

        let temp_container_file = dir.join("current_submission.tar");
        let temp_container_diff_file = dir.join("current_submission.tar.rsyncdiff");
        let last_submission_id_file = dir.join("last_submission_id.txt");
        let last_submission_rsync_signature_file = dir.join("last_submission_rsyncsig.bin");
        let last_submission_container_file = dir.join("last_submission.tar");

        Ok(ClientState {
            course_config,
            auth_token,

            temp_container_file,
            temp_container_diff_file,
            last_submission_id_file,
            last_submission_rsync_signature_file,
            last_submission_container_file,
        })
    }

    pub fn has_previous_submission(&self) -> bool {
        self.last_submission_id_file.exists() && self.last_submission_rsync_signature_file.exists()
    }

    pub fn dir() -> PathBuf {
        PathBuf::from_str(DEFAULT_DIR).unwrap()
    }
}

impl ClientStateError {
    pub fn should_prompt_for_token(&self) -> bool {
        match self {
            ClientStateError::MissingDirectory => true,
            ClientStateError::MissingSecretToken(_) => true,
            _ => false,
        }
    }
}

impl Display for ClientStateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ClientStateError::MissingDirectory => {
                write!(f, "Missing config directory {:?}", ClientState::dir())
            }
            ClientStateError::MissingServerBaseUrl => {
                write!(f, "Server url must be given with --server=... when not configured in .test-gadget/course.json")
            }
            ClientStateError::MissingSecretToken(path) => {
                write!(f, "Missing or empty secret token file: {:?}", path)
            }
            ClientStateError::LoginFailed(e) => {
                write!(f, "Login failed: {}", e)
            }
            ClientStateError::LoginResponseParseFailed(e) => {
                write!(f, "Failed to parse login response: {}", e)
            }
            ClientStateError::FailedToInit(e) => {
                write!(f, "{}", e)
            }
            ClientStateError::FailedToReadConfigFile(path, e) => {
                write!(f, "Failed to read config file {:?}: {}", path, e)
            }
            ClientStateError::FailedToParseConfigFile(path, e) => {
                write!(f, "Failed to parse config file {:?}: {}", path, e)
            }
            ClientStateError::FailedToReadSecretToken(path, e) => {
                write!(f, "Failed to read secret token file {:?}: {}", path, e)
            }
        }
    }
}
