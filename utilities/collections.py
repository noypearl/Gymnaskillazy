from typing import List, Any, Hashable


def is_empty(col):
    return not col

def filter_list_of_dicts_by_kv(l: List[dict], k: Hashable, v: Any) -> List[dict]:
    """
    Filters a list of dictionaries by a KV pair where . Value is neutralized if string.
    :param l: the original list of dicts
    :param k: key to filter by
    :param v: value to filter by
    :return: the filtered list of dicts
    """
    return [item for item in l if neutralize_str(item[k]) == neutralize_str(v)]

def get_all_values_of_k(l: List[dict], k: Hashable) -> list:
    return [i[k] for i in l]

def uniquify(l: list) -> list:
    """
    :param l: collection to remove duplications from
    :return: copy of l, with duplicates removed, sorted asc
    """
    return sorted(list(dict.fromkeys(l)))

def neutralize_str(s: str) -> str:
    if isinstance(s, str):
        return s.strip().lower()
    return s

def filter_cell_list_by_value(l: list, v: str):
    return [cell for cell in l if neutralize_str(cell.value) == v]

def get_most_recent_record(l: list):
    return max(l, key=lambda cell: cell.row)

def filter_out_empty_members(l: list, header=True) -> list:
    result = [i for i in l if not is_empty(i)]
    return result[1:] if header else result
