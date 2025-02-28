document.addEventListener("DOMContentLoaded", function() {
    let selectedRole = "";

    window.nextPage = function(pageNumber) {
        if (pageNumber === 2) {
            updateDisciplines();
        }
        showPage(pageNumber);
    };

    window.prevPage = function(pageNumber) {
        if (pageNumber === 2) {
            updateDisciplines();
        }
        showPage(pageNumber);
    };

    function showPage(pageNumber) {
        document.querySelectorAll(".form").forEach(page => {
            page.classList.remove("active");
        });
        document.getElementById(`page${pageNumber}`).classList.add("active");
    }

    function updateDisciplines() {
        const disciplineOptions = {
            "clinician": ["Dental", "Medicine Allopathic", "Medicine Osteopathic", "Nursing", "Occumpational Therapy", "Physical Therapy", "Physician Assistant"],
            "anatomist": ["Dental", "Medicine Allopathic", "Medicine Osteopathic", "Nursing", "Occumpational Therapy", "Physical Therapy", "Physician Assistant"],
            "both": ["Dental", "Medicine Allopathic", "Medicine Osteopathic", "Nursing", "Occumpational Therapy", "Physical Therapy", "Physician Assistant"],
        };

        selectedRole = document.querySelector('input[name="profession"]:checked')?.value;
        const container = document.getElementById("disciplineOptions");
        container.innerHTML = "";

        if (selectedRole && disciplineOptions[selectedRole]) {
            disciplineOptions[selectedRole].forEach(discipline => {
                const label = document.createElement("label");
                label.innerHTML = `<input type="checkbox" name="discipline" value="${discipline}"> ${discipline}`;

                container.appendChild(label);
                container.appendChild(document.createElement("br"));
            });
        }
    }
});