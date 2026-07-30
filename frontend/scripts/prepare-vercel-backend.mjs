import { access, cp, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";


const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendDirectory = path.resolve(scriptDirectory, "..");
const source = path.resolve(frontendDirectory, "..", "backend");
const destination = path.resolve(frontendDirectory, "backend");

if (!destination.startsWith(`${frontendDirectory}${path.sep}`)) {
  throw new Error("Refusing to prepare a backend outside the frontend directory.");
}

try {
  await access(source);
  await rm(destination, { recursive: true, force: true });
  await cp(source, destination, {
    recursive: true,
    filter: (entry) => {
      const normalized = entry.replaceAll("\\", "/");
      return !(
        normalized.includes("/__pycache__/") ||
        normalized.includes("/.pytest_cache/") ||
        normalized.includes("/tests/")
      );
    }
  });
  console.log("Synchronized FastAPI backend from the repository root.");
} catch {
  try {
    await access(destination);
  } catch {
    throw new Error(
      "Backend source is unavailable and no deploy mirror was packaged."
    );
  }
  console.log("Using the packaged FastAPI backend mirror.");
}
