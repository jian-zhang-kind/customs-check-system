const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

const DOCUMENT_SUFFIXES = [".pdf", ".png", ".jpg", ".jpeg"]
const PHOTO_SUFFIXES = [".png", ".jpg", ".jpeg"]

export function validateUpload(file: File, group: "document" | "photo"): string | null {
  const suffix = suffixOf(file.name)
  const allowed = group === "document" ? DOCUMENT_SUFFIXES : PHOTO_SUFFIXES
  if (!suffix || !allowed.includes(suffix)) {
    return "类型不支持"
  }
  if (file.size === 0) {
    return "缺文件"
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return "文件超过 8MB"
  }
  return null
}

function suffixOf(filename: string): string {
  const dot = filename.lastIndexOf(".")
  if (dot < 0) {
    return ""
  }
  return filename.slice(dot).toLowerCase()
}
