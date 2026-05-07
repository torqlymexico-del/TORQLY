document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.getAttribute("data-confirm") || "¿Confirmas esta acción?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    const addExtraButton = document.querySelector("[data-add-extra]");
    const extraContainer = document.querySelector("[data-extra-container]");
    if (addExtraButton && extraContainer) {
        addExtraButton.addEventListener("click", () => {
            const row = document.createElement("div");
            row.className = "extra-row";
            row.innerHTML = `
                <input type="text" name="extra_description" placeholder="Extra o upsell">
                <input type="number" step="0.01" name="extra_quantity" placeholder="1" value="1">
                <input type="number" step="0.01" name="extra_unit_price" placeholder="0.00">
                <select name="extra_apply_commission">
                    <option value="true">Comisionable</option>
                    <option value="false">Sin comision</option>
                </select>
            `;
            extraContainer.appendChild(row);
        });
    }
});
