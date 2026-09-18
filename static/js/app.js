// JavaScript próprio do FenixSchool -- o comportamento do layout (sidebar,
// menus) já vem de static/vendor/kiaalap/main.js.

// Cascata província → município: cada <option> de um <select> de município
// gerado por apps.core.widgets.MunicipalitySelect traz um atributo
// data-province com o código da respectiva província. Sem uma província
// seleccionada (ou com uma que não tem nenhum município correspondente já
// nas opções), o município não mostra nada para escolher -- nunca a lista
// completa das 185 do país inteiro.
function initProvinceMunicipalityCascade() {
    document.querySelectorAll("select").forEach((municipalitySelect) => {
        if (!municipalitySelect.name.endsWith("municipality")) return;
        if (municipalitySelect.dataset.cascadeInit) return;
        municipalitySelect.dataset.cascadeInit = "1";

        const provinceName = municipalitySelect.name.replace(/municipality$/, "province");
        const provinceSelect = document.querySelector(`select[name="${provinceName}"]`);
        if (!provinceSelect) return;

        const allOptions = Array.from(municipalitySelect.options);

        function applyFilter() {
            const provinceCode = provinceSelect.value;
            const previousValue = municipalitySelect.value;
            municipalitySelect.innerHTML = "";

            allOptions.forEach((option) => {
                const optionProvince = option.dataset.province;
                if (!option.value || optionProvince === provinceCode) {
                    municipalitySelect.appendChild(option);
                }
            });

            if (
                provinceCode &&
                Array.from(municipalitySelect.options).some((o) => o.value === previousValue)
            ) {
                municipalitySelect.value = previousValue;
            } else {
                municipalitySelect.value = "";
            }
        }

        provinceSelect.addEventListener("change", applyFilter);
        applyFilter();
    });
}

document.addEventListener("DOMContentLoaded", initProvinceMunicipalityCascade);
