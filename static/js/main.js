// Confirmation before submitting checkout
document.addEventListener("DOMContentLoaded", function () {
  const checkoutForm = document.getElementById("checkoutForm");
  if (checkoutForm) {
    checkoutForm.addEventListener("submit", function (e) {
      const confirmOrder = confirm(
        "Are you sure you want to place this order?"
      );
      if (!confirmOrder) {
        e.preventDefault();
      }
    });
  }

  // Toast-like success message fade out
  const flashMessages = document.querySelectorAll(".flash");
  flashMessages.forEach((msg) => {
    setTimeout(() => (msg.style.display = "none"), 3000);
  });
});
