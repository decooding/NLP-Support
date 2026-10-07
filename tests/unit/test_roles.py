def test_roles_registry_integrity():
    from pathlib import Path

    roles_dir = Path(".roles")
    assert roles_dir.exists() and roles_dir.is_dir()

    expected_roles = [
        "1_nlp_engineer.md",
        "2_llm_safety_engineer.md",
        "3_backend_engineer.md",
        "4_qa_devops_engineer.md",
        "5_researcher_paper_author.md",
        "README.md",
    ]
    for role_file in expected_roles:
        f = roles_dir / role_file
        assert f.exists(), f"Role file {role_file} is missing"
        assert f.stat().st_size > 0, f"Role file {role_file} is empty"
