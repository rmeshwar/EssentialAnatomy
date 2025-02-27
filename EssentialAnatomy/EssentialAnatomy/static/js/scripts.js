// CHANGED: We have updated the logic to fetch from parsed_structure.json for direct children
document.addEventListener("DOMContentLoaded", function() {
    let selectedRole = "";
    let directChildren = [];  // Will hold the direct children from "Clinician" or "Anatomist"

    window.nextPage = function(pageNumber) {
        if (pageNumber === 2) {
            loadDisciplines();
        }
        showPage(pageNumber);
    };

    window.prevPage = function(pageNumber) {
        showPage(pageNumber);
    };

    function showPage(pageNumber) {
        document.querySelectorAll(".form").forEach(page => {
            page.classList.remove("active");
        });
        document.getElementById(`page${pageNumber}`).classList.add("active");
    }

    // CHANGED: loadDisciplines() will fetch the direct children of "Clinician" or "Anatomist" 
    // from parsed_structure.json (via a local request).
    function loadDisciplines() {
        selectedRole = document.querySelector('input[name="profession"]:checked')?.value;

        // If the user hasn't chosen a role, do nothing or show alert
        if (!selectedRole) {
            alert("Please select a profession first.");
            return;
        }

        // We'll fetch the JSON file and then display direct children accordingly
        fetch(PARSED_STRUCTURE_URL)
            .then(response => response.json())
            .then(data => {
                let container = document.getElementById("disciplineOptions");
                container.innerHTML = "";

                // Depending on the chosen role
                let children = [];
                if (selectedRole === "clinician") {
                    // direct children = keys in data["Clinician"]["subgroups"]
                    if (data["Clinician"] && data["Clinician"]["subgroups"]) {
                        children = Object.keys(data["Clinician"]["subgroups"]);
                    }
                } else if (selectedRole === "anatomist") {
                    // direct children = the items in data["Anatomist"]["specialties"].map(s => s.name)
                    if (data["Anatomist"] && data["Anatomist"]["specialties"]) {
                        children = data["Anatomist"]["specialties"].map(obj => obj.name);
                    }
                } else if (selectedRole === "both") {
                    // We'll combine both sets
                    let c_children = [];
                    let a_children = [];
                    if (data["Clinician"] && data["Clinician"]["subgroups"]) {
                        c_children = Object.keys(data["Clinician"]["subgroups"]);
                    }
                    if (data["Anatomist"] && data["Anatomist"]["specialties"]) {
                        a_children = data["Anatomist"]["specialties"].map(obj => obj.name);
                    }
                    children = [...c_children, ...a_children];
                }

                directChildren = children;

                // Render as checkboxes
                directChildren.forEach(child => {
                    const label = document.createElement("label");
                    label.innerHTML = `<input type="checkbox" name="discipline" value="${child}"> ${child}`;
                    container.appendChild(label);
                    container.appendChild(document.createElement("br"));
                });
            })
            .catch(err => {
                console.error("Error loading structure:", err);
            });
    }

    // CHANGED: On clicking the Submit button on page3, gather data and send to server
    const submitBtn = document.getElementById("submitSelections");
    submitBtn.addEventListener("click", function() {
        const selectedProf = document.querySelector('input[name="profession"]:checked')?.value;
        if (!selectedProf) {
            alert("Please go back and select a profession.");
            return;
        }

        // Collect chosen disciplines
        let chosenDisciplines = [];
        document.querySelectorAll('input[name="discipline"]:checked').forEach(chk => {
            chosenDisciplines.push(chk.value);
        });

        // Collect chosen body regions
        let chosenRegions = [];
        document.querySelectorAll('input[name="region"]:checked').forEach(chk => {
            chosenRegions.push(chk.value);
        });

        // Build the data payload
        let payload = {
            profession: selectedProf,
            disciplines: chosenDisciplines,
            regions: chosenRegions
        };

        // CHANGED: We do an AJAX POST to /generate-report/ with our new structure
        fetch("/generate-report/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Network response was not OK");
            }
            return response.json();
        })
        .then(data => {
            // The server will return a { download_url: ... } or { error: ... }
            if (data.download_url) {
                // Trigger download
                const link = document.createElement('a');
                link.href = data.download_url;
                link.download = 'survey_report.pdf';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else if (data.error) {
                alert("Error generating report: " + data.error);
            }
        })
        .catch(error => {
            console.error("Error generating report:", error);
            alert("Error generating report: " + error);
        });
    });
});
