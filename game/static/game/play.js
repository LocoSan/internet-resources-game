const form = document.querySelector("#coin-form");
const button = form.querySelector("button");
const status = document.querySelector("#game-status");

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    try {
        const response = await fetch(form.action, {
            method: "POST",
            headers: {"X-CSRFToken": form.elements.csrfmiddlewaretoken.value}
        });
        if (!response.ok || response.redirected) {
            throw new Error("Не удалось сохранить клик.");
        }
        const progress = await response.json();
        for (const key of ["score", "level", "clicks", "coins"]) {
            document.querySelector("#" + key).textContent = progress[key];
        }
        status.textContent = "Прогресс сохранён.";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});
