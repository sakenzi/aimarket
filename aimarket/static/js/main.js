(function () {
  const toast = document.createElement("div");
  toast.style.position = "fixed";
  toast.style.right = "16px";
  toast.style.bottom = "16px";
  toast.style.padding = "12px 14px";
  toast.style.borderRadius = "14px";
  toast.style.border = "1px solid rgba(255,255,255,.16)";
  toast.style.background = "rgba(0,0,0,.45)";
  toast.style.backdropFilter = "blur(10px)";
  toast.style.color = "#fff";
  toast.style.fontFamily = "Arial, sans-serif";
  toast.style.fontSize = "14px";
  toast.style.boxShadow = "0 18px 50px rgba(0,0,0,.35)";
  toast.style.display = "none";
  toast.style.zIndex = "9999";
  document.body.appendChild(toast);

  function showToast(text) {
    toast.textContent = text;
    toast.style.display = "block";
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => (toast.style.display = "none"), 1400);
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".card__btn");
    if (!btn) return;
    showToast("Добавлено в корзину (мок) ✅");
  });
})();
