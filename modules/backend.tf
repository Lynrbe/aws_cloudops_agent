terraform {
  cloud {
    organization = "your-org"
    workspaces {
      name = "rag-infra"
    }
  }
}
