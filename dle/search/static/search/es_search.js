/* global instantsearch algoliasearch */

// Basic auth with username/password is not supported - bug: see https://github.com/searchkit/searchkit/issues/1235
const sk = new Searchkit({
    connection: {
        host: "http://localhost:8000/api/v1/searchkit", // TODO remove hardcoding for deployment
    },
    search_settings: {
        highlight_attributes: ["section_name", "drug_label_product_name", "drug_label_generic_name"],
        snippet_attributes: ["section_text"],
        search_attributes: ["drug_label_product_name", "section_name", "section_text", "drug_label_generic_name"],
        result_attributes: ["id", "label_product_id", "section_name", "section_text", "drug_label_product_name", "drug_label_generic_name", "drug_label_source", "drug_label_link", "drug_label_version_date", "drug_label_product_number"],
        facet_attributes: [
            "drug_label_source",
            {
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
    },
    }, { debug: true })

//   const res = await request
//     .query("rash")
//     .execute({
//         facets: true,
//         hits: {
//             size: 10,
//             from: 0
//         }
//     })

client = SearchkitInstantsearchClient(sk)

const search = instantsearch({
    indexName: "productsection",
    searchClient: client
});

async function vectorizeText(query){
    const response = await fetch("http://localhost:8000/api/v1/vectorize", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ "query": query })
    })
    const vector = await response.json();
    return vector;
}

// const results = await client.handleRequest(req.body, {
//     hooks: {
//         beforeSearch: async (searchRequests) => {
//         const [uiRequest, ...restRequests] = searchRequests
    
//         // get an image embedding from the query text
//         // const imageEmbedding = await getImageEmbeddingFromQueryText(uiRequest.params.query)
//         const textVector = await vectorizeText(uiRequest.params.query)
    
//         // extends the query to do a hybrid search with KNN search and text search
//         // https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search.html
//         return [
//             {
//             ...uiRequest,
//             body: {
//                 ...uiRequest.body,
//                 "knn": {
//                 "field": "image-vector",
//                 "query_vector": textVector,
//                 "k": 10,
//                 "num_candidates": 100
//                 },
//             },
//             },
//             restRequests,
//         ];
        
//         },
//     }
// });

search.addWidgets([
    instantsearch.widgets.searchBox({
        container: "#searchbox"
    }),
    instantsearch.widgets.currentRefinements({
        container: "#current-refinements"
    }),
    instantsearch.widgets.menuSelect({
        container: "#section-name-filter",
        attribute: "section_name",
        limit: 100
    }),
    instantsearch.widgets.refinementList({
        container: "#drug-label-source-filter",
        attribute: "drug_label_source"
    }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-product-name-filter",
        attribute: "drug_label_product_name",
        limit: 100
    }),
    instantsearch.widgets.menuSelect({
        container: "#drug-label-generic-name-filter",
        attribute: "drug_label_generic_name",
        limit: 100
    }),
    instantsearch.widgets.hits({
        container: "#hits",
        templates: {
            item(hit, { html, components }) {
                return html`
                <h2>
                    ${components.Highlight({ attribute: 'drug_label_product_name', hit })}
                </h2>
                <h3>
                    Generic Name: ${components.Highlight({ attribute: 'drug_label_generic_name', hit })}
                </h3>
                <h3>
                    Section: ${components.Highlight({ attribute: 'section_name', hit })}
                </h3>
                <ul>
                    <li>Source: ${hit.drug_label_source}</li>
                    <li>Version Date: ${hit.drug_label_version_date}</li>
                    <li>Product Number: ${hit.drug_label_product_number}</li>
                    <li>Link: <a href="${hit.drug_label_link}">${hit.drug_label_link}</a></li>
                </ul>
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
        items: [
            { label: '10 hits per page', value: 10, default: true },
            { label: '20 hits per page', value: 20 },
            { label: '50 hits per page', value: 50 }
        ],
    })
]);

search.start();