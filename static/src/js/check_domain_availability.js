document.getElementById("subdomain_input").addEventListener("keyup", async function (event) {
    let input = document.getElementById("subdomain_input");
    let errmsg = document.getElementById("subdomain_input_error");
    let submitButton = document.getElementById("subdomain_request_submit");


    const enteredSubdomain = input.value.trim().toLowerCase();
    const domainRegex = /^(?!-)[a-z0-9-]{1,63}(?<!-)$/;

    if (!domainRegex.test(enteredSubdomain)) {
        errmsg.innerText = "Invalid subdomain: only letters, numbers, and hyphens allowed. Cannot start or end with a hyphen.";
        errmsg.style.display = "block";
        submitButton.style.pointerEvents = "none";
        submitButton.style.cursor = "not-allowed";
        return; // stop here, don’t check availability
    }

    try {
        const response = await fetch("/check-subdomains", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.result.subdomains && data.result.subdomains.includes(enteredSubdomain)) {
            errmsg.innerText ="This subdomain is already in use";
            errmsg.style.display = "block";
            submitButton.style.pointerEvents = "none";
            submitButton.style.cursor = "not-allowed";
        } else {
            errmsg.style.display = "none";
            submitButton.style.pointerEvents = "auto";
            submitButton.style.cursor = "pointer";
        }

    } catch (err) {
        console.error("Subdomain check failed:", err);
    }
});
