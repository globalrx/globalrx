/* global instantsearch algoliasearch */

// Basic auth with username/password is not supported - bug: see https://github.com/searchkit/searchkit/issues/1235
var globalSearchTerm = '';
const sk = new Searchkit({
    connection: {
        host: ELASTIC_HOST, // Set by the Django template in which this file is embedded
    },
    search_settings: {
        highlight_attributes: [
            "section_name",
            "drug_label_product_name", 
            "drug_label_generic_name"
        ],
        snippet_attributes: ["section_text"],
        search_attributes: [
            "drug_label_product_name",
            "section_name",
            "section_text",
            "drug_label_generic_name",
            "drug_label_source",
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
            "drug_label_id" // Django DL ID e.g. 48464
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
            }, {
                field: "drug_label_generic_name.keyword",
                type: "string",
                attribute: "drug_label_generic_name",
            }
        ],
        fragment_size: 300
    }
})

async function vectorizeText(query) {
    const response = await fetch("http://localhost:8000/api/v1/vectorize", {
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

client = SearchkitInstantsearchClient(sk, {
    hooks: {
        beforeSearch: async (searchRequests) => {
            const [uiRequest] = searchRequests

            query = uiRequest.request.params.query
            if (!query) {
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
})

const search = instantsearch({
    indexName: "productsection",
    searchClient: client,
    routing: true
});

search.addWidgets([
    instantsearch.widgets.searchBox({
        queryHook(query, search) {
            globalSearchTerm = query;
            search(query);
        },
    }),
    instantsearch.widgets.currentRefinements({
        container: "#current-refinements"
    }),
    instantsearch.widgets.menuSelect({
        container: "#section-name-filter",
        attribute: "section_name",
        field: "section_name.keyword",
        limit: 100
    }),
    instantsearch.widgets.refinementList({
        container: "#drug-label-source-filter",
        attribute: "drug_label_source",
        field: "drug_label_source.keyword",
    }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-product-name-filter",
        attribute: "drug_label_product_name",
        field: "drug_label_product_name.keyword",
        limit: 10000
    }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-generic-name-filter",
        attribute: "drug_label_generic_name",
        field: "drug_label_generic_name.keyword",
        limit: 10000
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
                return html `
                      <a href="${singleItemUrl}"style='font-weight:bold'>${components.Highlight({ attribute: 'drug_label_product_name', hit })}</a> <br />
                      ${components.Highlight({ attribute: 'drug_label_generic_name', hit })}<br />
                      Section Name: ${components.Highlight({ attribute: 'section_name', hit })} <br />
                      Source: ${hit.drug_label_source}<br />
                      Version Date: ${hit.drug_label_version_date}<br />
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