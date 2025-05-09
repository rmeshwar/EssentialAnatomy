// CHANGED: We have updated the logic to fetch from parsed_structure.json for direct children
document.addEventListener("DOMContentLoaded", function() {
    let selectedRole = "";
    let directChildren = [];  // Will hold the direct children from "Clinician" or "Anatomist"
    let clinicianSpecialtyMap = {};   // php -> { specialty : [subspecialties] }

    loadDisciplines();
    loadRegions();

    fetch("/api/clinician_specialties/")
    .then(r => r.json())
    .then(data => {
        clinicianSpecialtyMap = data;
        buildClinicianSpecialtyUI();     // build once we have the PHP list
    })
    .catch(err => console.error("Could not load clinician specialties", err));


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

    function loadRegions() {
        fetch(SECTIONS_API)
            .then(res => res.json())
            .then(data => {
                const wrapper = document.getElementById("regionOptions");
                wrapper.innerHTML = "";
    
                Object.entries(data).forEach(([sectionName, subs]) => {
                    // parent checkbox
                    const pId = `section-${sectionName.replace(/\s+/g, "_")}`;
                    wrapper.insertAdjacentHTML("beforeend", `
                        <label class="fw-bold">
                          <input type="checkbox"
                                 class="region-parent"
                                 id="${pId}"
                                 data-section="${sectionName}"> ${sectionName}
                        </label><br/>
                    `);
    
                    // children
                    subs.forEach(subName => {
                        const cId = `sub-${subName.replace(/\s+/g, "_")}`;
                        wrapper.insertAdjacentHTML("beforeend", `
                            <div style="margin-left:25px">
                               <label>
                                 <input type="checkbox"
                                        class="region-child"
                                        data-parent="${sectionName}"
                                        id="${cId}"
                                        value="${subName}">
                                     ${subName}
                               </label>
                            </div>
                        `);
                    });
                    wrapper.insertAdjacentHTML("beforeend", "<hr/>");
                });
    
                attachRegionEvents();
            })
            .catch(err => console.error("Could not load regions", err));
    }

    function attachRegionEvents() {
        // parent toggles children
        document.querySelectorAll(".region-parent").forEach(parent => {
            parent.addEventListener("change", function () {
                const sect = this.dataset.section;
                document.querySelectorAll(`.region-child[data-parent="${sect}"]`)
                        .forEach(c => c.checked = this.checked);
            });
        });
    
        // children keep parent in-sync
        document.querySelectorAll(".region-child").forEach(child => {
            child.addEventListener("change", function () {
                const sect = this.dataset.parent;
                const parentBox = document.querySelector(`.region-parent[data-section="${sect}"]`);
                const anyChecked = [...document.querySelectorAll(`.region-child[data-parent="${sect}"]`)]
                                   .some(c => c.checked);
                parentBox.checked = anyChecked;   // if none remain checked, un-tick parent
            });
        });
    }

    function attachSpecialtyEvents(){
        // PHP parent → all its specialties
        document.querySelectorAll(".spec-php-parent").forEach(pp => {
            pp.addEventListener("change", function(){
                const php = this.dataset.php;
                document.querySelectorAll(`.spec-checkbox[data-php="${php}"], .subspec-checkbox[data-php="${php}"]`)
                    .forEach(c => c.checked = this.checked);
            });
        });
    
        // specialty checkbox → its subs
        document.querySelectorAll(".spec-checkbox").forEach(sp => {
            sp.addEventListener("change", function(){
                const php=this.dataset.php, spec=this.value;
                document.querySelectorAll(`.subspec-checkbox[data-php="${php}"][data-spec="${spec}"]`)
                    .forEach(s => s.checked=this.checked);
            });
        });
    }
    

    function buildClinicianSpecialtyUI() {
        const wrap = document.getElementById("clinicianSpecialtyOptions");
        wrap.innerHTML = "";
    
        Object.entries(clinicianSpecialtyMap).forEach(([php, specs]) => {
            // PHP heading (appears only if the PHP itself is present in the child list)
            if (!document.querySelector(`.child-clin[value="${php}"]`)) return;
    
            const phpDivId = `spec-${php.replace(/\s+/g,"_")}`;
            wrap.insertAdjacentHTML("beforeend", `
                <label class="fw-bold">
                  <input type="checkbox" class="spec-php-parent" data-php="${php}">
                  ${php} &nbsp;<em>(all specialties)</em>
                </label><br/>
                <div id="${phpDivId}" class="spec-php-children" style="margin-left:25px"></div>
            `);
    
            const inner = document.getElementById(phpDivId);
            Object.entries(specs).forEach(([spec, subs]) => {
                const specId = `spec-${php}-${spec}`.replace(/\s+/g,"_");
                inner.insertAdjacentHTML("beforeend", `
                    <label>
                      <input type="checkbox" class="spec-checkbox"
                             data-php="${php}" value="${spec}"
                             id="${specId}">
                      ${spec}
                    </label><br/>
                `);
                if (subs.length) {
                    const subDivId = `${specId}-subs`;
                    inner.insertAdjacentHTML("beforeend", `<div id="${subDivId}" style="margin-left:25px"></div>`);
                    const subDiv = document.getElementById(subDivId);
                    subs.forEach(sub => {
                        subDiv.insertAdjacentHTML("beforeend", `
                            <label>
                              <input type="checkbox" class="subspec-checkbox"
                                     data-php="${php}" data-spec="${spec}" value="${sub}">
                              ${sub}
                            </label><br/>
                        `);
                    });
                }
            });
        });
    
        // show container only if there is at least one PHP with specialties
        document.getElementById("clinicianSpecialtyContainer").style.display =
            wrap.children.length ? "block" : "none";
    
        // parents ↔ children sync
        attachSpecialtyEvents();
    }
    

    function getTotalSelectedColumns(){
        let total = 0;
    
        // Anatomist block (unchanged)
        const anatParent = document.getElementById("anatomistParent").checked;
        total += anatParent ? 1 : document.querySelectorAll(".child-anat:checked").length;
    
        // Clinician PHP level
        const clinParent = document.getElementById("clinicianParent").checked;
        const checkedPHPs = document.querySelectorAll(".child-clin:checked").length;
        total += clinParent ? 1 : checkedPHPs;
    
        // Clinician specialties (only add if their PHP isn’t counted via parent‑php checkbox)
        document.querySelectorAll(".spec-checkbox:checked").forEach(sp => {
            const php = sp.dataset.php;
            const phpChecked = document.querySelector(`.child-clin[value="${php}"]`)?.checked;
            if (!phpChecked) total += 1;
        });
    
        // subspecialties (count only if their parent specialty isn’t ticked)
        document.querySelectorAll(".subspec-checkbox:checked").forEach(ss => {
            const php  = ss.dataset.php;
            const spec = ss.dataset.spec;
            const specBox = document.querySelector(`.spec-checkbox[data-php="${php}"][value="${spec}"]`);
            const phpChecked = document.querySelector(`.child-clin[value="${php}"]`)?.checked;
            if (!phpChecked && !(specBox && specBox.checked)) {
                total += 1;
            }
        });
    
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
        let regionPayload = [];
        document.querySelectorAll(".region-parent").forEach(parent => {
            if (!parent.checked) return;   // completely unselected section

            const sect = parent.dataset.section;
            const children = [...document.querySelectorAll(`.region-child[data-parent="${sect}"]`)];
            const deselected = children.filter(c => !c.checked).map(c => c.value);

            if (deselected.length === 0) {
                regionPayload.push({ parent: sect });            // whole section included
            } else {
                regionPayload.push({ parent: sect, deselected }); // include section w/ omissions
            }
        });

        // ---- NEW: clinician specialties / subspecialties ----
        document.querySelectorAll(".spec-checkbox:checked").forEach(sp => {
            const php  = sp.dataset.php;
            const spec = sp.value;
            const grandKey = `${php} / ${spec}`;
            finalColumns.push({ parent:"Clinician", child:php, grandchild:spec });
        });

        // add individual subspecialties (only if they are NOT implicitly selected above)
        document.querySelectorAll(".subspec-checkbox:checked").forEach(ss => {
            const php  = ss.dataset.php;
            const spec = ss.dataset.spec;
            const sub  = ss.value;

            // skip if parent specialty is already selected
            const parentSpecChecked = document.querySelector(`.spec-checkbox[data-php="${php}"][value="${spec}"]`)?.checked;
            if (parentSpecChecked) return;

            finalColumns.push({ parent:"Clinician", child:php, grandchild:spec, greatgrandchild:sub });
        });


        // Build the data payload
        let payload = {
            profession: selectedProf,
            columns: finalColumns,
            regions: regionPayload
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
