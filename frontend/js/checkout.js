
(function () {
    /**
     * Updated Checkout logic for Cookie-based Auth and Razorpay.
     */

    const API_BASE_URL = "http://127.0.0.1:5000/api";
    const payButton = document.getElementById("rzp-button1");
    console.log("Pay button found:", payButton);
    if (payButton) {
        payButton.onclick = async function (e) {
            e.preventDefault();

            const amount = document.getElementById("payAmount").value;

            if (!amount) {
                alert("Please enter amount");
                return;
            }
            payButton.disabled = true;
            payButton.innerText = "Processing...";

            try {
                console.log("Creating order...");

                // Step 1: Create order
                const response = await fetch(`${API_BASE_URL}/create-order`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"

                    },
                    body: JSON.stringify({ amount: amount }),
                    credentials: "include"
                });

                if (response.status === 401) {
                    alert("Session expired. Please login again.");
                    window.location.href = "index.html";
                    return;
                }

                const order = await response.json();
                console.log("Order created:", order);

                // Step 2: Razorpay options
                const options = {
                    key: "rzp_test_SKKLnsVKaGkFav",
                    amount: order.amount,
                    currency: "INR",
                    name: "Payment App",
                    description: "Test Transaction",
                    order_id: order.id,

                    // SUCCESS HANDLER
                    handler: async function (response) {
                        console.log("Payment Success received from Razorpay");

                        const verifyRes = await fetch(`${API_BASE_URL}/verify-payment`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            credentials: "include", // Send cookies for verification
                            body: JSON.stringify({
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature
                            })
                        });

                        if (verifyRes.ok) {
                            alert("Payment Successful!");
                            window.location.href = "history.html"; // Redirect to history on success
                        } else {
                            alert("Payment Verification Failed!");
                        }
                        payButton.disabled = false;
                        payButton.innerText = "Pay Now";
                    },

                    // MODAL CLOSED (User clicked 'X')
                    modal: {
                        ondismiss: async function () {
                            console.log("User closed the payment popup.");

                            // Inform backend to set status to 'Failed'
                            await fetch(`${API_BASE_URL}/verify-payment`, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                credentials: "include",
                                body: JSON.stringify({
                                    razorpay_order_id: order.id,
                                    razorpay_payment_id: null,
                                    razorpay_signature: null
                                })
                            });
                            payButton.disabled = false;
                            payButton.innerText = "Pay Now";
                        }
                    }
                };

                const rzp = new Razorpay(options);

                // FAILURE HANDLER (Payment declined by bank/network)
                rzp.on('payment.failed', async function (response) {
                    console.log("Payment Failed event triggered");

                    const orderId = response?.error?.metadata?.order_id || order.id;

                    await fetch(`${API_BASE_URL}/verify-payment`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "include",
                        body: JSON.stringify({
                            razorpay_order_id: orderId,
                            razorpay_payment_id: null,
                            razorpay_signature: null
                        })
                    });

                    alert("Payment Failed! " + response.error.description);
                    payButton.disabled = false;
                    payButton.innerText = "Pay Now";
                });

                rzp.open();

            } catch (error) {
                console.error("Connection Error:", error);
                alert("Could not connect to the server.");
                payButton.disabled = false;
                payButton.innerText = "Pay Now";
            }
        };
    }

})();