// main.js

/**
 * Disables the checkout button and shows a spinner to indicate processing.
 * @param {HTMLFormElement} form - The checkout form element.
 */
function handleCheckoutSubmit(form) {
    const btn = document.getElementById("checkout-btn");

    if (form && btn) {
        // Disable the button and show spinner
        btn.disabled = true;
        btn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Processing...
        `;

        // Optional: Prevent double submit fallback
        setTimeout(() => {
            btn.disabled = true;
        }, 500); // Lock again after small delay
    }
}
