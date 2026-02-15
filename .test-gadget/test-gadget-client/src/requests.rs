pub fn create_reqwest_client() -> Result<reqwest::blocking::Client, reqwest::Error> {
    reqwest::blocking::Client::builder()
        .timeout(None)
        .gzip(true)
        .brotli(true)
        .deflate(true)
        .build()
}
