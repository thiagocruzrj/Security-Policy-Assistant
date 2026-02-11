variable "project_name" {
  description = "Base name for all resources"
  type        = string
  default     = "sectbot"
}

variable "environment" {
  description = "Deployment environment (dev, stage, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "openai_model_name" {
  description = "Azure OpenAI chat model name"
  type        = string
  default     = "gpt-4o"
}

variable "embedding_model_name" {
  description = "Azure OpenAI embedding model name"
  type        = string
  default     = "text-embedding-3-small"
}

variable "search_sku" {
  description = "Azure AI Search SKU (basic required for semantic ranker)"
  type        = string
  default     = "basic"
}
