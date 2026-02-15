
This program is used to build and efficiently upload Docker-based projects to Test Gadget.

A precompiled version for Linux, MacOS and Windows is available in the project template.
This source code is made available for those who run exotic systems, and for those
who are suspicious of downloading random programs from the internet :)

To compile this, [install Rust](https://www.rust-lang.org/tools/install)
and run `cargo build --release`.

The program will be compiled to `target/release/test-gadget-client`.
Run it with `--help` to see options.

The program must be run in the directory of the project you're working on.
The project must have a file `.test-gadget/course.json` with contents like this:

```json
{
  "server_base_url": "https://test-gadget.compilers.how"
}
```
