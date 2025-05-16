# llm-reader-policy.hcl
path "llm/data/google" {
  capabilities = ["read", "list"]
}
path "llm/data/google/" { # Include trailing slash as per error hint
  capabilities = ["read", "list"]
}
# For UI functionality like listing versions, metadata access might also be needed:
path "llm/metadata/google" {
  capabilities = ["list"]
}
path "llm/metadata/google/" {
  capabilities = ["list"]
}