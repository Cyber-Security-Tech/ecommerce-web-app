function handleCheckoutSubmit(form) {
    const btn = document.getElementById("checkout-btn");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...`;
}
