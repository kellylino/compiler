use std::path::PathBuf;

use anyhow::{anyhow, Result};
use clap::{Args, Parser, Subcommand};
use test_gadget_client::{apply_rsync_diff, submit, SubmitMode};

#[derive(Parser)]
#[command(version, about, long_about = None)]
#[command(propagate_version = true)]
struct CliArgs {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    #[command(about = "Builds the project with Docker and submits it.")]
    Submit(SubmitCommand),
    #[command(subcommand, about = "Commands for internal use.")]
    Internal(InternalCommand),
}

#[derive(Args)]
struct SubmitCommand {
    #[arg(
        help = "If given, the container from the given TAR file is submitted instead of building one from a Dockerfile"
    )]
    container_file: Option<PathBuf>,
    #[arg(long, help = "Overrides the server URL given in .mooc/course.json")]
    server: Option<String>,
    #[arg(
        long,
        help = "Always submits the whole container instead of attempting to send only the diff with the last submission."
    )]
    no_diff: bool,
    #[arg(
        long,
        help = "Doesn't try to submit the whole container if sending a diff failed."
    )]
    only_diff: bool,
    #[arg(long, help = "Keeps the last submission file around for debugging.")]
    keep_last_submission: bool,
    #[arg(long, help = "Asks the server to not actually store the submission. Used for testing.")]
    dry_run: bool,
}

#[derive(Subcommand)]
enum InternalCommand {
    #[command(about = "Applies a fast_rsync diff to a file.")]
    ApplyRsyncDiff(ApplyRsyncDiffCommand),
}

#[derive(Args)]
struct ApplyRsyncDiffCommand {
    #[arg(long, help = "The diff file to apply.")]
    diff: PathBuf,
    #[arg(long, help = "The file original file that the diff is for.")]
    source: PathBuf,
    #[arg(long, help = "The file to write the result to.")]
    destination: PathBuf,
    #[arg(long, help = "The expected sha256 of the resulting file.")]
    sha256: Option<String>,
    #[arg(long, help = "The maximum size of the resulting file.")]
    size_limit: Option<usize>,
}

fn main() -> Result<()> {
    env_logger::init();
    let args = CliArgs::parse();
    match args.command {
        Commands::Submit(cmd) => {
            if cmd.only_diff && cmd.no_diff {
                return Err(anyhow!("--only-diff and --no-diff are mutually exclusive"));
            }
            let mode = if cmd.only_diff {
                SubmitMode::DiffOnly
            } else if cmd.no_diff {
                SubmitMode::NoDiff
            } else {
                SubmitMode::TryDiffFirst
            };
            submit(
                cmd.container_file.as_ref().map(|p| p.as_path()),
                cmd.server.as_ref().map(|s| s.as_str()),
                mode,
                cmd.keep_last_submission,
                cmd.dry_run,
            )
        }
        Commands::Internal(cmd) => match cmd {
            InternalCommand::ApplyRsyncDiff(cmd) => apply_rsync_diff(
                &cmd.diff,
                &cmd.source,
                &cmd.destination,
                cmd.sha256.as_ref().map(|s| s.as_str()),
                cmd.size_limit,
            ),
        },
    }
}
