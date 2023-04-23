/* global instantsearch algoliasearch */

// See below - need to figure out how to disable caching
// import { createNullCache } from 'https://cdn.jsdelivr.net/npm/@algolia/cache-common/+esm';

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
       //     console.log(`getQuery - simpleQueryString - ${query}`);
         //   console.log(search_attributes);
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
        beforeSearch: async (searchRequests) => {
            const [uiRequest] = searchRequests

            var query = uiRequest.request.params.query
        //    console.log(`beforeSearch: ${query}`)
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

// Update querytype when radio button is changed
const radioGroup = document.getElementsByName("search-type");
radioGroup.forEach(function(radio) {
    radio.addEventListener("change", function() {
        if(this.checked){
            queryType = this.value;
          //  console.log(queryType);
        }
        // Empty the search cache when the query type changes
        // This must occur after changing the query type
        search.refresh();
    });
})