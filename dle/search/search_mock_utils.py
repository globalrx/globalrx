from .models import MockDrugLabel

"""
    id: int
    source: int
    generic_name: str
    brand_name: str
    application_num: str
    ndc: str
    unii: str
    set_id: str
    manufacturer: str
    class_name_id: int
    marketing_category: int
    country: int
    version: date
    creation_date: datetime
    owner: int
"""

SEARCH_RESULTS = [
    MockDrugLabel(
        drug_id=1,
        drug_generic_name="Ibuprofen",
        manufacturer="Pfizer",
        text="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas maximus condimentum interdum. Aenean vel tellus vel mauris egestas ultrices. Donec porta accumsan dolor sit amet convallis. Sed mollis, eros eget bibendum iaculis, ex ex interdum leo, at ullamcorper velit magna eu tortor. Nunc eu ex ut metus hendrerit convallis. Duis felis tortor, vestibulum at hendrerit ut, varius ut dui. Suspendisse et risus dolor. Pellentesque id fermentum mauris. Curabitur a justo blandit, suscipit odio vel, congue enim. Mauris at tristique neque.",
    ),
    MockDrugLabel(
        drug_id=2,
        drug_generic_name="Acetaminophen",
        manufacturer="Moderna",
        text="Maecenas eget dolor dignissim arcu interdum faucibus. Nulla hendrerit sem enim, blandit varius turpis feugiat rhoncus. Nullam venenatis nulla erat, vel varius enim elementum id. Sed auctor velit id mi mattis mollis. Quisque hendrerit nisi neque, sit amet porta nisl aliquam id. Etiam pretium, lacus aliquet feugiat commodo, est ipsum consectetur sem, ac viverra nisl odio vel elit. Sed erat lacus, ornare nec turpis nec, tincidunt convallis mi.",
    ),
    MockDrugLabel(
        drug_id=3,
        drug_generic_name="Nyquil",
        manufacturer="GsK",
        text="Suspendisse potenti. Duis non odio vitae nulla commodo vestibulum sit amet sed libero. Fusce pellentesque, nibh nec congue commodo, enim metus porta mi, eu eleifend sem risus et lectus. Etiam a nunc quis mauris dictum convallis. Sed pellentesque massa a pretium feugiat. Suspendisse ut ornare ipsum. Etiam iaculis massa diam, in volutpat magna semper a. Nulla placerat, ligula eu gravida mollis, orci justo laoreet nibh, at dictum ante purus at lectus. Donec convallis magna est, quis scelerisque metus faucibus dignissim.",
    ),
    MockDrugLabel(
        drug_id=4,
        drug_generic_name="Asprin",
        manufacturer="Bayer",
        text="Fusce sit amet fringilla sem. Pellentesque volutpat enim leo, at aliquet velit cursus eget. Maecenas at mollis ex. Praesent id massa pretium, auctor sem convallis, vestibulum sem.",
    ),
]
