use std::fs;
use std::io::{BufWriter, Write};
use std::path::Path;

use anyhow::{Context, Result};
use log::info;
use memmap2::Mmap;
use sha2::{Digest, Sha256};

pub fn apply_rsync_diff(
    diff_path: &Path,
    source_path: &Path,
    destination_path: &Path,
    sha256: Option<&str>,
    size_limit: Option<usize>,
) -> Result<()> {
    let execute = || {
        let diff_file = fs::File::open(diff_path)
            .with_context(|| format!("Failed to open diff file {}", diff_path.display()))?;
        let source_file = fs::File::open(source_path)
            .with_context(|| format!("Failed to open source file {}", source_path.display()))?;
        let mut destination_file = fs::File::create(destination_path).with_context(|| {
            format!(
                "Failed to create destination file {}",
                destination_path.display()
            )
        })?;

        let diff_mmap = unsafe { Mmap::map(&diff_file).context("Failed to mmap diff file")? };
        let source_mmap = unsafe { Mmap::map(&source_file).context("Failed to mmap source file")? };
        info!(
            "Source file: {} bytes, diff file: {} bytes",
            source_mmap.len(),
            diff_mmap.len()
        );

        let mut destination_writer = BufWriter::new(&mut destination_file);
        if let Some(sha256) = sha256 {
            let mut destination_writer = HashingWriter::new(destination_writer, Sha256::new());
            apply_diff(
                &source_mmap,
                &diff_mmap,
                &mut destination_writer,
                size_limit,
            )?;
            let digest_hex = hex::encode(destination_writer.into_digest().finalize());
            info!("SHA256 of result: {:?}", digest_hex);
            if digest_hex.to_lowercase() != sha256.to_lowercase() {
                return Err(anyhow::anyhow!(
                    "SHA256 does not match expected: {}",
                    digest_hex,
                ));
            }
        } else {
            apply_diff(
                &source_mmap,
                &diff_mmap,
                &mut destination_writer,
                size_limit,
            )?;
        }

        Ok(())
    };

    execute().map_err(|e| {
        // Best effort cleanup
        let _ = fs::remove_file(destination_path);
        e
    })
}

fn apply_diff<W: Write>(
    source_mmap: &[u8],
    diff_mmap: &[u8],
    mut destination_writer: W,
    size_limit: Option<usize>,
) -> Result<()> {
    if let Some(size_limit) = size_limit {
        info!("Applying diff with size limit {}", size_limit);
        fast_rsync::apply_limited(
            &source_mmap,
            &diff_mmap,
            &mut destination_writer,
            size_limit,
        )?;
    } else {
        info!("Applying diff without size limit");
        fast_rsync::apply(&source_mmap, &diff_mmap, &mut destination_writer)?;
    }
    Ok(())
}

struct HashingWriter<W: Write, D: Digest> {
    writer: W,
    digest: D,
}

impl<W: Write, D: Digest> HashingWriter<W, D> {
    pub fn new(writer: W, digest: D) -> Self {
        Self { writer, digest }
    }

    pub fn into_digest(self) -> D {
        self.digest
    }
}

impl<W: Write, D: Digest> Write for HashingWriter<W, D> {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.writer.write(buf)?;
        self.digest.update(buf);
        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        self.writer.flush()?;
        Ok(())
    }
}
