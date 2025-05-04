// Importujeme Tabulator a jeho CSS priamo tu
// Astro/Vite spracuje tieto importy počas build procesu
import { Tabulator } from 'tabulator-tables';
import 'tabulator-tables/dist/css/tabulator.min.css'; // Importujeme základné CSS

// Funkcia na získanie dát vložených do HTML
function getTableData() {
    const dataElement = document.getElementById('table-data');
    if (!dataElement) {
        console.error("Element with ID 'table-data' not found.");
        return [];
    }
    try {
        return JSON.parse(dataElement.textContent || '[]');
    } catch (e) {
        console.error("Error parsing table data from JSON:", e);
        return [];
    }
}

// Funkcia na formátovanie dátumu (musíme ju definovať aj na klientovi)
const formatClientDate = (dateString) => {
    if (!dateString) return 'N/A';
    // Jednoduché formátovanie, môžeme použiť aj pokročilejšie
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('sk-SK');
    } catch (e) {
        console.error("Chyba pri formátovaní dátumu:", dateString, e);
        return 'Neplatný dátum';
    }
};

// Získanie dát
const documents = getTableData();

// Inicializácia Tabulatora
if (documents.length > 0) {
    let allSummariesVisible = false; // Stav pre hromadné zobrazenie/skrytie
    const table = new Tabulator("#documents-table", {
        data: documents,           // Naše dáta
        height: "100%",            // <<< PRIDANÉ: Nastavenie výšky tabuľky
        maxHeight:"100%",
        layout: "fitDataStretch",  // Rozloženie stĺpcov
        responsiveLayout: "collapse", // Skrytie stĺpcov na menších obrazovkách
        pagination: "local",       // Lokálna paginácia
        paginationSize: 20,        // Počet riadkov na stránku
        paginationSizeSelector: [10, 20, 50, 100], // Možnosti počtu riadkov
        rowFormatter: function(row) {
            // Vytvoríme div pre zhrnutie, ktorý bude štandardne skrytý
            var element = row.getElement();
            var data = row.getData();
            var summaryText = '-'; // Predvolený text, ak nie je analýza

            if (data.has_analysis) {
                summaryText = '<b>Zhrnutie:</b> '+data.analyza?.zhrnutie || 'Bez zhrnutia textu.';
                if (data.analyza) {
                    try {
                        const analyzaJson = JSON.stringify(data.analyza, null, 4);
                        summaryText += `\n\n<hr>\n\n<strong>Kompletná analýza (JSON):</strong>\n${analyzaJson}`;
                    } catch (e) {
                        console.error("Chyba pri stringify data.analyza:", data.analyza, e);
                        summaryText += '\n\n<hr>\n\n<strong>Chyba pri generovaní JSON analýzy.</strong>';
                    }
                } else {
                    summaryText += '\n\n<hr>\n\n<strong>Objekt analýzy nie je dostupný.</strong>';
                }
            }

            var summaryContainer = document.createElement("div");
            summaryContainer.className = "row-summary"; // Trieda pre ľahšiu selekciu a štýlovanie
            summaryContainer.style.display = "none"; // Štandardne skryté
            summaryContainer.style.padding = "10px 15px";
            summaryContainer.style.borderTop = "1px solid #eee";
            summaryContainer.style.backgroundColor = "#f9f9f9";
            summaryContainer.style.whiteSpace = "pre-wrap"; // Aby sa rešpektovali nové riadky v zhrnutí
            summaryContainer.innerHTML = `${summaryText}`;

            element.appendChild(summaryContainer);
        },
        columns: [                 // Definícia stĺpcov
            { title: "Dátum", field: "datum", hozAlign: "left", sorter: "date", sorterParams:{ format:"YYYY-MM-DD" }, formatter: (cell) => formatClientDate(cell.getValue()), width: 90 },
            { title: "Kraj", field: "kraj", hozAlign: "left", headerFilter: "input", width: 120 },
            { title: "Okres", field: "okres", hozAlign: "left", headerFilter: "input", width: 120 },
            { title: "Typ zásahu", field: "analyza.typ_zasahu", hozAlign: "left", headerFilter: "input", width: 120, formatter: (cell) => {
                const hasAnalysis = cell.getData().has_analysis;
                if (!hasAnalysis) return 'Bez analýzy';
                const value = cell.getValue();
                if (Array.isArray(value)) return value.join(', ');
                return value || 'N/A';
            }},
            { title: "Typ územia", field: "analyza.typ_uzemia", hozAlign: "left", headerFilter: "input", width: 120, formatter: (cell) => {
                const hasAnalysis = cell.getData().has_analysis;
                if (!hasAnalysis) return '-';
                const value = cell.getValue();
                if (Array.isArray(value)) return value.join(', ');
                return value || 'N/A';
            }},
            { title: "Názov dokumentu", field: "nazov", hozAlign: "left", headerFilter: "input", minWidth: 300, formatter: (cell) => {
                const url = cell.getData().url;
                const nazov = cell.getValue();
                return `<a href="${url}" target="_blank" rel="noopener noreferrer">${nazov}</a>`;
            }},
        ],
    });
    table.on("rowClick", function(e, row){
        console.log('rowClick()');
        var element = row.getElement();
        var summaryContainer = element.querySelector(".row-summary");
        if (summaryContainer) {
            summaryContainer.style.display = summaryContainer.style.display === "none" ? "block" : "none";
        }
    });

    // Funkcionalita pre tlačidlo na hromadné zobrazenie/skrytie
    const toggleBtn = document.getElementById('toggle-summaries-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            allSummariesVisible = !allSummariesVisible; // Zmeníme stav
            const rows = table.getRows();
            rows.forEach(row => {
                const element = row.getElement();
                const summaryContainer = element.querySelector(".row-summary");
                if (summaryContainer) {
                    summaryContainer.style.display = allSummariesVisible ? "block" : "none";
                }
            });
            toggleBtn.textContent = allSummariesVisible ? 'Skryť všetky zhrnutia' : 'Zobraziť všetky zhrnutia';
        });
    }
} else {
    // Optional: Handle the case where there are no documents (e.g., hide the toggle button)
    const toggleBtn = document.getElementById('toggle-summaries-btn');
    if (toggleBtn) toggleBtn.style.display = 'none';
}