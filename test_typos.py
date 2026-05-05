from search_engine import SearchEngine

def test_typos():
    engine = SearchEngine()
    test_queries = [
        "rde cars at saket",        # rde -> red (typo)
        "blu suvs at chandi chwk",  # blu -> blue (abbr), chandi -> chandni (typo), chwk -> chowk (abbr)
        "white biek near cp",       # biek -> bike (typo)
        "luxry sedan in sakat",     # luxry -> luxury (typo), sakat -> saket (typo)
        "gren auto",                # gren -> green (typo)
        "sedan at cp",              # exact
        "bik near hauz khas",       # bik -> bike (abbr)
        "blk suv",                  # blk -> black (abbr)
        "slvr car",                 # slvr -> silver (abbr)
    ]
    
    print(f"{'Query':<30} | {'Color':<10} | {'Type':<15} | {'Location':<15}")
    print("-" * 80)
    
    for query in test_queries:
        parsed = engine.parse_query(query)
        color = parsed.get('color') or 'None'
        vehicle_type = parsed.get('type') or (parsed.get('type_list')[0] if parsed.get('type_list') else 'None')
        location = parsed.get('location') or 'None'
        print(f"{query:<30} | {color:<10} | {vehicle_type:<15} | {location:<15}")

if __name__ == "__main__":
    test_typos()
