from radar.classify import pick_tier

KW = {"gold": ["intune", "rollout", "monitoring"], "silver": ["data scientist", "recommend"], "bronze": ["power bi"]}


def test_generic_term_in_body_does_not_tier():
    assert pick_tier("accountant. we manage the rollout and monitoring of invoices", KW, "Accountant") == (None, [])


def test_generic_term_in_title_tiers():
    assert pick_tier("monitoring engineer", KW, "Monitoring Engineer")[0] == "Gold"


def test_specific_term_in_title_tiers():
    assert pick_tier("intune", KW, "Intune Engineer")[0] == "Gold"


def test_one_body_hit_is_not_enough_two_are():
    assert pick_tier("we use power bi", KW, "Analyst")[0] is None
    assert pick_tier("we use intune and power bi", {**KW, "gold": ["intune", "power bi"]}, "Analyst")[0] == "Gold"


def test_whole_word_only():
    assert pick_tier("recommendation letters", KW, "Clerk") == (None, [])
