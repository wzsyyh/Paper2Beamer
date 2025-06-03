from modelscope import snapshot_download

model_root = "models"
snapshot_download("Lixiang/marker-pdf", local_dir="models")
