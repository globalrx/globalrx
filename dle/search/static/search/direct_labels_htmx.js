// Handle searchKit searches
// Need to handle when the form is submitted, when the form is cleared
// Also handle when there is a query in the URL on initial page load
// Add event listeners
let searchbox = document.getElementById('searchbox');
searchbox.addEventListener("searchkit_ready",
    (e) => {
        console.log("searchkit ready");
        form = document.querySelector('.ais-SearchBox-form');
        // Fire HTMX in case this is on initial page load; submit event doesn't fire,
        // but we could have a query in the URL populating the search box
        q = document.querySelector('.ais-SearchBox-input').value;
        console.log(q);
        htmx.ajax(
            "GET",
            `/data/search_label_htmx?query=${q}`, {
                target: "#drug-label-search-results",
                swap: "innerHTML"
            }
        );

        form.addEventListener("submit", (e) => {
            console.log("submit event")
            query = document.querySelector('.ais-SearchBox-input').value;
            htmx.ajax(
                "GET",
                `/data/search_label_htmx?query=${query}`, {
                    target: "#drug-label-search-results",
                    swap: "innerHTML"
                }
            );
        })

        form.addEventListener("reset", (e) => {
            console.log("reset event")
            htmx.ajax(
                "GET",
                // Submit an empty query and clear the results box
                `/data/search_label_htmx?query=`, {
                    target: "#drug-label-search-results",
                    swap: "innerHTML"
                }
            );
        })
    })