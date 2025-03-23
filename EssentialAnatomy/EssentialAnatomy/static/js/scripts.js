// CHANGED: We have updated the logic to fetch from parsed_structure.json for direct children
document.addEventListener("DOMContentLoaded", function() {
    let selectedRole = "";
    let directChildren = [];  // Will hold the direct children from "Clinician" or "Anatomist"
    loadDisciplines();

    window.nextPage = function(pageNumber) {
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

    function getTotalSelectedColumns() {
        let total = 0;

        // 1) Check if “Anatomist” parent is checked
        const anatParentChecked = document.getElementById("anatomistParent").checked;
        const anatChildren = document.querySelectorAll(".child-anat:checked");
        if (anatParentChecked) {
            // That entire group is 1 column
            total += 1;
        } else {
            // Each child is a separate column
            total += anatChildren.length;
        }

        // 2) Check if “Clinician” parent is checked
        const clinParentChecked = document.getElementById("clinicianParent").checked;
        const clinChildren = document.querySelectorAll(".child-clin:checked");
        if (clinParentChecked) {
            total += 1;
        } else {
            total += clinChildren.length;
        }

        return total;
    }

    // CHANGED: loadDisciplines() will fetch the direct children of "Clinician" or "Anatomist" 
    // from parsed_structure.json (via a local request).
    function loadDisciplines() {
        console.log("DEBUG: Fetching parsed_structure.json...");
        // Ensure both containers are visible
        document.getElementById("anatomistContainer").style.display = "block";
        document.getElementById("clinicianContainer").style.display = "block";
    
        fetch("/api/get_filtered_disciplines/")
            .then(response => response.json())
            .then(data => {
                
                // Fill Anatomist Children (filtered from ProcessedResponseAnatomy)
                const anatomistChildren = data["Anatomist"] || [];
                const anatDiv = document.getElementById("anatomistChildren");
                anatDiv.innerHTML = ""; // Clear previous entries
                anatomistChildren.forEach(child => {
                    const label = document.createElement("label");
                    label.innerHTML = `<input type="checkbox" class="child-anat" name="discipline" value="${child}" data-parent="Anatomist"> ${child}`;
                    anatDiv.appendChild(label);
                    anatDiv.appendChild(document.createElement("br"));
                });
    
                // Fill Clinician Children (filtered from ProcessedResponseClinician)
                const clinicianChildren = data["Clinician"] || [];
                const clinDiv = document.getElementById("clinicianChildren");
                clinDiv.innerHTML = ""; // Clear previous entries
                clinicianChildren.forEach(child => {
                    const label = document.createElement("label");
                    label.innerHTML = `<input type="checkbox" class="child-clin" name="discipline" value="${child}" data-parent="Clinician"> ${child}`;
                    clinDiv.appendChild(label);
                    clinDiv.appendChild(document.createElement("br"));
                });
            })
            .catch(err => {
                console.error("Error loading filtered disciplines:", err);
            });
    }

    // CHANGED: On clicking the Submit button on page3, gather data and send to server
    const submitBtn = document.getElementById("submitSelections");
    submitBtn.addEventListener("click", function() {
        const selectedProf = "both";
        if (!selectedProf) {
            alert("Please go back and select a profession.");
            return;
        }

        // Collect chosen disciplines
        let chosenDisciplines = [];
        document.querySelectorAll('input[name="discipline"]:checked').forEach(chk => {
            chosenDisciplines.push(chk.value);
        });

        // We'll store columns in an array, but also store child expansions in an object
        // so we can handle partial or full selection
        let finalColumns = [];
        let expansions = {}; // expansions["Anatomist"] = ["Dentistry", "Nursing", etc..]

        // Single role approach
        if (selectedProf === "clinician" || selectedProf === "anatomist") {
            // Just gather whichever are checked
            const checkedDiscs = document.querySelectorAll('input[name="discipline"]:checked');
            checkedDiscs.forEach(chk => {
                finalColumns.push({ parent: chk.dataset.parent, child: chk.value });
            });
        } else if (selectedProf === "both") {
            // We check the "Anatomist" parent
            const anatParentChecked = document.getElementById("anatomistParent").checked;
            const allAnatChildren = document.querySelectorAll(".child-anat");
            const anatCheckedChildren = [...allAnatChildren].filter(chk => chk.checked).map(chk => chk.value);

            if (anatParentChecked) {
                const deselectedAnatChildren = [...allAnatChildren].filter(chk => !chk.checked).map(chk => chk.value);
                finalColumns.push({
                    parent: "Anatomist",
                    children: anatCheckedChildren.length === allAnatChildren.length ? null : anatCheckedChildren,
                    deselected: deselectedAnatChildren.length > 0 ? deselectedAnatChildren : null
                });
            } else {
                anatCheckedChildren.forEach(child => {
                    finalColumns.push({ parent: "Anatomist", child });
                });
            }

            // Similarly for "Clinician"
            const clinParentChecked = document.getElementById("clinicianParent").checked;
            const allClinChildren = document.querySelectorAll(".child-clin");
            const clinCheckedChildren = [...allClinChildren].filter(chk => chk.checked).map(chk => chk.value);

            if (clinParentChecked) {
                const deselectedClinChildren = [...allClinChildren].filter(chk => !chk.checked).map(chk => chk.value);
                finalColumns.push({
                    parent: "Clinician",
                    children: clinCheckedChildren.length === allClinChildren.length ? null : clinCheckedChildren,
                    deselected: deselectedClinChildren.length > 0 ? deselectedClinChildren : null
                });
            } else {
                clinCheckedChildren.forEach(child => {
                    finalColumns.push({ parent: "Clinician", child });
                });
            }
        }

        // Collect chosen body regions
        let chosenRegions = [];
        document.querySelectorAll('input[name="region"]:checked').forEach(chk => {
            chosenRegions.push(chk.value);
        });

        // Build the data payload
        let payload = {
            profession: selectedProf,
            columns: finalColumns,
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
            if (data.download_url) {
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

    // Parent check event listeners
    ["anatomistParent", "clinicianParent"].forEach(parentId => {
        const parentElement = document.getElementById(parentId);
        if (parentElement) {
            parentElement.addEventListener("change", function() {
                const isChecked = this.checked;
                document.querySelectorAll(`.${parentId === "anatomistParent" ? "child-anat" : "child-clin"}`)
                    .forEach(chk => chk.checked = isChecked);
            });
        }
    });

    // Limit selection to 9 columns
    document.addEventListener("change", function(e) {
        if (e.target.name === "discipline") {
            if (getTotalSelectedColumns() > 9) {
                e.target.checked = false;
                alert("You can only select up to 9 columns total!");
            }
        }
    });
});
