def _blank(value) -> bool:
    return value is None or str(value).strip() == ""


def accept_or_discard(link, name, price, article, shop: str) -> bool:
    """Return True if the product is complete enough to store; otherwise print and discard."""
    missing = []
    if _blank(link):
        missing.append("url")
    if _blank(name):
        missing.append("name")
    if _blank(price):
        missing.append("price")
    if _blank(article):
        missing.append("article")
    if not missing:
        return True
    print(
        f"discard shop={shop} missing={','.join(missing)} "
        f"url={link!r} name={name!r} price={price!r} article={article!r}"
    )
    return False
