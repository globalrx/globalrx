/* global instantsearch algoliasearch */

// See below - need to figure out how to disable caching
// import { createNullCache } from 'https://cdn.jsdelivr.net/npm/@algolia/cache-common/+esm';

function createDrugLabelDirectMatchDiv(hit) {
    const newLineItem = document.createElement("li");
    newLineItem.className = "ais-Hits-item";
    newLineItem.id = 'drug-label-name-match-div';
    newLineItem.innerHTML = `<h2>${hit.drug_label_product_name}</h2>`;
    
    // drug_labels.forEach(item => {
    //     console.log(item)
    // });

    // for(const drug_label in drug_labels[0]) {
    //     console.log('drug_label', drug_label);
    //     console.log('drug_label.id', drug_label['id']);
    //     console.log('drug_label.marketer', drug_label['marketer']);
    //     console.log('drug_label.version_date', drug_label['version_date']);
    // }

    // the following logic in the setTimeout method takes the class where 
    // the list of results are displayed, and checks for an exact match with 
    // one of the drugs in the database. If found, it creates an extra 
    // drug specific search box at the top and fill sit with drug specific data
    // There's a two second delay since there's no dom related hook in the
    // searchkit library we're using
    setTimeout(() => {
        console.log("Delayed for 1 second");

        console.log('drug_labels', drug_labels);
        console.log('drug_labels[0]', drug_labels[0]);    

        const parentList = document.getElementsByClassName('ais-Hits-list');
        const possibleExistingElement = document.getElementById(newLineItem.id);

        console.log('possibleExistingElement', possibleExistingElement);
        console.log('hit', hit);

        if(possibleExistingElement !== null && parentList.length > 0) { // TODO check this logic
            // here we check if existing elemtn exists and if so remove it 
            // so we can add a new element as needed
            parentList[0].removeChild(possibleExistingElement);
            console.log('its not null so return');
        }

        if(parentList.length == 0) {
            console.log('parentLis tis 0 so return');
            return;
        }

        // TODO make sure this updates when the search terms change.
        // NOT 100% sure that's happening right now

        console.log('hit inside method', hit);

        const parentElement = parentList[0];


        parentElement.insertBefore(newLineItem, parentElement.children[0]);
    }, "1000"); // <- 1 second delay in milliseconds
    // I don't love this implmeentation but there's no hooks for this library
    // other than before search and after search and after search shockingly
    // is called first and nether of these contain changes to the dom.
}

var globalSearchTerm = '';
var queryType = 'match'; // knn, simpleQueryString, match

const sk = new Searchkit({
    connection: {
        host: SEARCHKIT_SERVICE, // Set by the Django template in which this file is embedded
    },
    // Need to figure out how to disable caching. Caching doesn't seem to work if we change
    // the search type, e.g. from match to simple_query_string or knn
    // See: https://www.algolia.com/doc/api-client/getting-started/customize/javascript/?client=javascript#caching-the-state-of-hosts
    // For now, running search.refresh() when we change the search type which seems to work
    // responsesCache: createNullCache(),
    // requestsCache: createNullCache(),
    search_settings: {
        highlight_attributes: [
            "section_name",
            "drug_label_product_name", 
            "drug_label_generic_name",
            "drug_label_marketer"
        ],
        snippet_attributes: [
            "section_text:300"
        ],
        search_attributes: [
            "drug_label_product_name",
            "section_name",
            "section_text",
            "drug_label_generic_name",
            "drug_label_source",
            "drug_label_marketer"
        ],
        result_attributes: [
            "id", // Django Section ID - string not int e.g. "980870". In most cases same as Elasticsearch _id
            "label_product_id", // Django Label Product ID e.g. 45703
            "section_name", // Normalized, e.g. "Date Of First Authorisation/Renewal Of The Authorisation"
            "section_text", // E.g. "Date of first authorisation: 25 June 2018"
            "drug_label_product_name", // e.g. DuoPlavin
            "drug_label_generic_name", // e.g. clopidogrelacetylsalicylic acid
            "drug_label_source", // e.g. EMA
            "drug_label_link", // https://www.ema.europa.eu/documents/product-information/duoplavin-epar-product-information_en.pdf
            "drug_label_version_date", // 2023-03-31
            "drug_label_product_number", // Does not currently exist in Elasticsearch
            "drug_label_id", // Django DL ID e.g. 48464
            "drug_label_marketer"
        ],
        facet_attributes: [
            {
                field: "drug_label_source", // Not drug_label_source.keyword, it's only indexed as keyword
                type: "string",
                attribute: "drug_label_source",
            }, {
                field: "section_name.keyword",
                type: "string",
                attribute: "section_name",
            }, {
                field: "drug_label_product_name.keyword",
                type: "string",
                attribute: "drug_label_product_name",
                // searchable: true - this works but only with refinementList widgets
            }, {
                field: "drug_label_generic_name.keyword",
                type: "string",
                attribute: "drug_label_generic_name",
            }, {
                field: "drug_label_marketer.keyword",
                type: "string",
                attribute: "drug_label_marketer",
            }
        ],
    }
}, {debug: true})

async function vectorizeText(query) {
    const response = await fetch(VECTORIZE_SERVICE, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "query": query
        })
    })
  const vector = await response.json();
  return vector;
}

const client = SearchkitInstantsearchClient(sk, {
    getQuery: (query, search_attributes) => {
        if(queryType == 'simpleQueryString'){
            console.log(`getQuery - simpleQueryString - ${query}`);
            console.log(search_attributes);
            return [
                {
                    simple_query_string: {
                        query,
                        fields: search_attributes
                    }
                }
            ]
        } else if (queryType=='match'){
            return [
                {
                    multi_match: {
                        query,
                        fields: search_attributes
                    }
                    
                }
            ]
        }

    },
    hooks: {
        onComponentUpdate: (prevProps, nextProps) => {
            console.log("Component updated:", prevProps, nextProps);
            alert('it hit');
            // Handle the component update here
        },
        onSearchError: (error) => {
            console.error("Search error:", error);
            // Handle the error here
        },
        afterSearch: async (searchRequests, searchResponses) => {
            console.log('afterSearch HOOK')
            console.log('results', searchResponses);
            console.log('searchRequests', searchRequests);
            console.log('globalSearchTerm', globalSearchTerm);
            // Manipulate the DOM here
            // const messageDiv = document.createElement("div");
            // console.log(messageDiv);
            // messageDiv.innerHTML = "hi there";x
            // const searchResultsDiv = document.getElementById("searchResults");
            // searchResultsDiv.appendChild(messageDiv);
            return searchResponses;
        },
        // TODO maybe update to use getKnnQuery: https://www.searchkit.co/docs/guides/customising-query
        beforeSearch: async (searchRequests) => {
            const [uiRequest] = searchRequests

            var query = uiRequest.request.params.query
            console.log(`beforeSearch: ${query}`)
            if (!query | !(queryType=='knn')) {
                return searchRequests;
            }

            const vectorizationRes = await vectorizeText(query);
            return searchRequests.map((sr) => {
                return {
                ...sr,
                body: {
                    ...sr.body,
                    knn: {
                    "field": "text_embedding",
                    "query_vector": vectorizationRes.vector,
                    "k": 10,
                    "num_candidates": 100
                    }
                }
                }
            })
        }
    }
});

const search = instantsearch({
  indexName: "productsection",
  searchClient: client,
  routing: true
});

search.addWidgets([
    instantsearch.widgets.searchBox({
        queryHook(query, search) {
            console.log('query', query);
            globalSearchTerm = query;
            console.log('globalSearchTerm', globalSearchTerm);
            console.log('is globalSearchTermBlank')
            search(query);
        },
        container: "#searchbox",
        searchAsYouType: false,
        showReset: true,
        showSubmit: true,
        showLoadingIndicator: true
    }),
    instantsearch.widgets.currentRefinements({
        container: "#current-refinements"
    }),
    instantsearch.widgets.menuSelect({
        container: "#section-name-filter",
        attribute: "section_name",
        field: "section_name.keyword",
        limit: 1000
    }),
    instantsearch.widgets.refinementList({
        container: "#drug-label-source-filter",
        attribute: "drug_label_source",
        field: "drug_label_source",
        limit: 10
    }),
    // Checkbox widget
    // instantsearch.widgets.refinementList({
    //     container: "#drug-label-product-name-filter",
    //     attribute: "drug_label_product_name",
    //     field: "drug_label_product_name.keyword",
    //     limit: 10,
    //     searchable: true,
    //     showMore: true,
    //     showMoreLimit: 10000
    // }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-product-name-filter",
        attribute: "drug_label_product_name",
        field: "drug_label_product_name.keyword",
        limit: 10000,
    }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-generic-name-filter",
        attribute: "drug_label_generic_name",
        field: "drug_label_generic_name.keyword",
        limit: 10000,
    }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-marketer-filter",
        attribute: "drug_label_marketer",
        field: "drug_label_marketer.keyword",
        limit: 10000,
    }),
    instantsearch.widgets.hits({
        container: "#hits",
        templates: {
            item(hit, {
                html,
                components
            }) {
                var singleItemUrl = '';
                if (globalSearchTerm == '') {
                    // no search term, no highlighting or we will error
                    singleItemUrl = `../data/single_label_view/${hit.drug_label_id}`;
                } else {
                    singleItemUrl = `../data/single_label_view/${hit.drug_label_id}, ${globalSearchTerm}`;
                }

                console.log('hit:', hit);
                console.log('hit.drug_label_product_name:', hit.drug_label_product_name);
                console.log('globalSearchTerm:', globalSearchTerm);
                console.log(globalSearchTerm == hit.drug_label_product_name);
                if(hit.drug_label_product_name == globalSearchTerm) {
                    console.log('they are equal');
                    createDrugLabelDirectMatchDiv(hit);
                }

                return html `
                      <input type="checkbox" name="compare" value="${hit.drug_label_id}" />
                      <a href="${singleItemUrl}"style='font-weight:bold'>${components.Highlight({ attribute: 'drug_label_product_name', hit })}</a> <br />
                      ${components.Highlight({ attribute: 'drug_label_generic_name', hit })}<br />
                      Section Name: ${components.Highlight({ attribute: 'section_name', hit })} <br />
                      Source: ${hit.drug_label_source}<br />
                      Version Date: ${hit.drug_label_version_date}<br />
                      Marketer: ${components.Highlight({ attribute: 'drug_label_marketer', hit })}<br />
                      <!-- DOESN'T EXIST IN ES YET Product Number: ${hit.drug_label_product_number}<br /> -->
                      Source Link: <a href="${hit.drug_label_link}">${hit.drug_label_link}</a><br />
                      <p>${components.Snippet({ attribute: 'section_text', hit })}</p>
                      `;
      }
    }
  }),
  instantsearch.widgets.pagination({
    container: "#pagination"
  }),
  instantsearch.widgets.hitsPerPage({
    container: '#hits-per-page',
    items: [{
      label: '10 hits per page',
      value: 10,
      default: true
    },
    {
      label: '20 hits per page',
      value: 20
    },
    {
      label: '50 hits per page',
      value: 50
    }
    ],
  })
]);

search.start();

const queryString = window.location.search;
console.log('queryString', queryString);
const urlParams = new URLSearchParams(queryString);
console.log('urlParams', urlParams);

globalSearchTerm = urlParams.get('productsection[query]');
console.log('productsection[query]', globalSearchTerm);

// Update querytype when radio button is changed
const radioGroup = document.getElementsByName("search-type");
radioGroup.forEach(function(radio) {
    radio.addEventListener("change", function() {
        if(this.checked){
            queryType = this.value;
            console.log(queryType);
        }
        // Empty the search cache when the query type changes
        // This must occur after changing the query type
        search.refresh();
    });
})