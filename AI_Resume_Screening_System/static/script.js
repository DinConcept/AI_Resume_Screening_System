// LOADING STATE
function showLoading() {
  const formBox = document.getElementById("formBox");
  const loading = document.getElementById("loading");
  if (formBox) formBox.style.display = "none";
  if (loading) loading.classList.add("active");
}

// CLOSE RESULT
function closeResult() {
  const resultBox = document.getElementById("resultBox");
  if (resultBox) {
    resultBox.style.opacity = "0";
    resultBox.style.transform = "translateY(20px)";
    setTimeout(() => {
      resultBox.style.display = "none";
      const formBox = document.getElementById("formBox");
      if (formBox) formBox.style.display = "block";
    }, 300);
  }
}

// FILE INPUT DISPLAY
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const dropZone = document.getElementById("dropZone");

if (fileInput && fileName) {
  fileInput.addEventListener("change", () => {
    const f = fileInput.files[0];
    fileName.textContent = f ? `✓  ${f.name}` : "";
  });
}

// Drag-and-drop highlight
if (dropZone) {
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  ["dragleave", "drop"].forEach((evt) =>
    dropZone.addEventListener(evt, () =>
      dropZone.classList.remove("drag-over"),
    ),
  );
}

// SCORE RING ANIMATION
window.addEventListener("DOMContentLoaded", () => {
  const ring = document.querySelector(".ring-fill");
  if (ring) {
    const final = ring.getAttribute("stroke-dasharray");
    ring.setAttribute("stroke-dasharray", "0 326.7");
    setTimeout(() => ring.setAttribute("stroke-dasharray", final), 100);
  }
});
