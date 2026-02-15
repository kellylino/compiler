use std::{
    fs,
    io::{BufWriter, Seek, Write},
    path::{Path, PathBuf},
    process::Command,
    sync::Arc,
    thread,
};

use anyhow::{anyhow, Result};
use log::info;
use memmap2::Mmap;
use serde::Deserialize;
use sha2::{Digest, Sha256};

use crate::{
    client_state::{ClientState, ClientStateError},
    requests::create_reqwest_client,
};

#[derive(Eq, PartialEq, Clone, Copy)]
pub enum SubmitMode {
    TryDiffFirst,
    DiffOnly,
    NoDiff,
}

// TODO: progress bar
pub fn submit(
    container_file_override: Option<&Path>,
    server_baseurl_override: Option<&str>,
    mode: SubmitMode,
    keep_last_submission: bool,
    dry_run: bool,
) -> Result<()> {
    preflight_check_docker()?;

    let attempts = 3;
    for _ in 0..attempts {
        let submit_result = submit_impl(
            container_file_override,
            server_baseurl_override,
            mode,
            keep_last_submission,
            dry_run,
        );
        match submit_result {
            Ok(r) => return Ok(r),
            Err(e) => {
                if is_auth_error(&e) {
                    println!("Authentication failed.");
                    ClientState::prompt_for_login_and_init(server_baseurl_override)?;
                    continue;
                } else {
                    return Err(e);
                }
            }
        }
    }
    return Err(anyhow!(
        "Failed to log in after {} authentication failures",
        attempts
    ));
}

fn is_auth_error(e: &anyhow::Error) -> bool {
    has_status_code(e, 401)
}

fn is_gone_error(e: &anyhow::Error) -> bool {
    has_status_code(e, 410)
}

fn has_status_code(e: &anyhow::Error, status: u16) -> bool {
    if e.is::<reqwest::Error>() {
        let re = e.downcast_ref::<reqwest::Error>().unwrap();
        re.status().map(|s| s.as_u16()) == Some(status)
    } else {
        false
    }
}

pub fn submit_impl(
    container_file_override: Option<&Path>,
    server_baseurl_override: Option<&str>,
    mode: SubmitMode,
    keep_last_submission: bool,
    dry_run: bool,
) -> Result<()> {
    let client_state = ClientState::load();

    let client_state = match client_state {
        Ok(c) => c,
        Err(e) => {
            if e.should_prompt_for_token() {
                ClientState::prompt_for_login_and_init(server_baseurl_override)?
            } else {
                return Err(e.into());
            }
        }
    };

    let server_baseurl = client_state
        .course_config
        .get_server_baseurl(server_baseurl_override)
        .ok_or_else(|| anyhow!("{}", ClientStateError::MissingServerBaseUrl))?;
    let container_file = if let Some(p) = container_file_override {
        p.to_path_buf()
    } else {
        println!("Building container...");
        build_container(&client_state)?;
        println!(
            "Container size: {:.2}MB",
            (client_state.temp_container_file.metadata()?.len() as f64) / 1024.0 / 1024.0
        );
        client_state.temp_container_file.clone()
    };

    let upload_result: UploadResult = if mode != SubmitMode::NoDiff
        && client_state.has_previous_submission()
    {
        println!("Uploading container (diff)...");
        match upload_container_with_diffing(
            &client_state,
            &server_baseurl,
            &container_file,
            dry_run,
        ) {
            Ok(r) => r,
            Err(e) => {
                if mode == SubmitMode::TryDiffFirst && !is_auth_error(&e) && !is_gone_error(&e) {
                    println!(
                        "Failed to upload diff so uploading full container instead: {}",
                        e
                    );

                    upload_container_without_diffing(
                        &client_state,
                        &server_baseurl,
                        &container_file,
                        dry_run,
                    )?
                } else {
                    return Err(e);
                }
            }
        }
    } else {
        println!("Uploading container...");
        upload_container_without_diffing(&client_state, &server_baseurl, &container_file, dry_run)?
    };

    if !dry_run {
        println!("Saving information about this submission...");
        store_last_submission(&client_state, &container_file, &upload_result.submission_id)?;
    }

    if keep_last_submission {
        fs::rename(
            &client_state.temp_container_file,
            &client_state.last_submission_container_file,
        )?;
    } else {
        let _ = fs::remove_file(&client_state.temp_container_file);
        let _ = fs::remove_file(&client_state.last_submission_container_file);
    }

    println!("Done!");
    Ok(())
}

fn build_container(client_state: &ClientState) -> Result<()> {
    if !PathBuf::from("Dockerfile").exists() {
        return Err(anyhow!("Dockerfile not found in current directory"));
    }
    let image_name = "test-gadget-submission:latest";

    let build_status = Command::new("docker")
        .arg("build")
        .arg("-t")
        .arg(image_name)
        .arg("--platform")
        .arg("linux/amd64")
        .arg(".")
        .status()?;
    if !build_status.success() {
        return Err(anyhow!("Failed to build Docker image"));
    }

    let save_status = Command::new("docker")
        .arg("save")
        .arg("-o")
        .arg(&client_state.temp_container_file)
        .arg(image_name)
        .status()?;
    if !save_status.success() {
        return Err(anyhow!("Failed to export Docker image"));
    }

    Ok(())
}

fn preflight_check_docker() -> Result<()> {
    // Intentionally simple "is Docker installed?" check.
    // We run this before attempting `docker build` so we can show a clear error message.
    let output = Command::new("docker").arg("--version").output();
    let blurb = "Docker does not seem to be available.\n\n\
Please install Docker (Docker Desktop or Docker Engine) and ensure the `docker` command works.\n\n";
    match output {
        Ok(o) if o.status.success() => Ok(()),
        Ok(o) => Err(anyhow!(
            "{}\
Error details:\n\
  exit code: {}\n\
  stdout: {}\n\
  stderr: {}\n",
            blurb,
            o.status,
            String::from_utf8_lossy(&o.stdout).trim(),
            String::from_utf8_lossy(&o.stderr).trim(),
        )),
        Err(e) => Err(anyhow!(
            "{}\
Error details: {}\n",
            blurb,
            e
        )),
    }
}

fn upload_container_with_diffing(
    client_state: &ClientState,
    server_baseurl: &str,
    container_file: &Path,
    dry_run: bool,
) -> Result<UploadResult> {
    let prev_signature = fs::read(&client_state.last_submission_rsync_signature_file)?;
    let prev_signature = fast_rsync::Signature::deserialize(prev_signature)?;
    let prev_signature = prev_signature.index();
    let last_submission_id = fs::read_to_string(&client_state.last_submission_id_file)?
        .trim()
        .to_string();
    let file = fs::File::open(&container_file)?;
    let mmap = Arc::new(unsafe { Mmap::map(&file) }?);

    info!("Calculating diff and hash...");
    let (hash, diff_file) = thread::scope(|s| -> Result<(String, fs::File)> {
        let hash_thread = {
            let mmap = mmap.clone();
            s.spawn(move || {
                let digest = hex::encode(Sha256::digest(mmap.as_ref()));
                info!("Hash calculated.");
                digest
            })
        };

        let diff_thread = {
            let mmap = mmap.clone();
            s.spawn(move || -> Result<fs::File> {
                let diff_path = &client_state.temp_container_diff_file;
                let mut diff_file = fs::OpenOptions::new()
                    .read(true)
                    .write(true)
                    .create(true)
                    .truncate(true)
                    .open(diff_path)?;
                {
                    let mut diff_writer = BufWriter::new(&mut diff_file);
                    fast_rsync::diff(&prev_signature, &mmap, &mut diff_writer)?;
                    diff_writer.flush()?;
                }
                info!("Diff calculated.");
                info!(
                    "Diff size: {:.2}MB (original size: {:.2}MB)",
                    (diff_file.metadata()?.len() as f64) / 1024.0 / 1024.0,
                    (mmap.len() as f64) / 1024.0 / 1024.0
                );
                diff_file.rewind()?;
                Ok(diff_file)
            })
        };

        let hash = hash_thread.join().unwrap();
        let diff_file = diff_thread.join().unwrap()?;
        Ok((hash, diff_file))
    })?;

    println!(
        "Diff size: {:.2}MB",
        (client_state.temp_container_diff_file.metadata()?.len() as f64) / 1024.0 / 1024.0
    );

    info!("Beginning upload...");
    let server_url = format!("{}/api/submit/diff", server_baseurl);
    let client = create_reqwest_client()?;
    let response = client
        .post(server_url)
        .query(&[
            ("sha256", &hash),
            ("prevId", &last_submission_id),
            ("dryRun", &dry_run.to_string()),
        ])
        .bearer_auth(&client_state.auth_token)
        .header("Content-Type", "application/octet-stream")
        .body(diff_file)
        .send()?
        .error_for_status()?;
    let result: UploadResult = serde_json::from_str(&response.text()?)?;
    info!("Diff uploaded successfully.");
    Ok(result)
}

fn upload_container_without_diffing(
    client_state: &ClientState,
    server_baseurl: &str,
    container_file: &Path,
    dry_run: bool,
) -> Result<UploadResult> {
    info!("Calculating hash...");
    let file = fs::File::open(&container_file)?;
    let hash = {
        let mmap = Arc::new(unsafe { Mmap::map(&file) }?);
        hex::encode(Sha256::digest(mmap.as_ref()))
    };

    info!("Beginning upload...");
    let server_url = format!("{}/api/submit", server_baseurl);
    let client = create_reqwest_client()?;
    let response = client
        .post(server_url)
        .query(&[("sha256", &hash), ("dryRun", &dry_run.to_string())])
        .bearer_auth(&client_state.auth_token)
        .header("Content-Type", "application/octet-stream")
        .body(file)
        .send()?
        .error_for_status()?;
    let result: UploadResult = serde_json::from_str(&response.text()?)?;
    info!("Uploaded successfully.");
    Ok(result)
}

fn store_last_submission(
    client_state: &ClientState,
    container_file: &Path,
    submission_id: &str,
) -> Result<()> {
    let file = fs::File::open(&container_file)?;
    let mmap = Arc::new(unsafe { Mmap::map(&file) }?);

    let mmap = mmap.clone();
    let signature = fast_rsync::Signature::calculate(
        mmap.as_ref(),
        fast_rsync::SignatureOptions {
            block_size: 512, // TODO: is this a good value?
            crypto_hash_size: 16,
        },
    );
    fs::write(
        &client_state.last_submission_rsync_signature_file,
        signature.serialized(),
    )?;

    fs::write(&client_state.last_submission_id_file, submission_id)?;

    Ok(())
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct UploadResult {
    submission_id: String,
}
