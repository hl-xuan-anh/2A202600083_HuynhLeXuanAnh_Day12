import os
import sys
import json
import logging

def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "[OK]" if passed else "[FAIL]"
    print(f"  {icon} {name}" + (f" - {detail}" if detail else ""))
    return {"name": name, "passed": passed}

def run_checks():
    results = []
    base = os.path.dirname(__file__)

    print("\n" + "=" * 55)
    print("  Production Readiness Check - Lab 6")
    print("=" * 55)

    # -- Files -----------------------------------------
    print("\n[Files] Required Files")
    results.append(check("Dockerfile exists",
                         os.path.exists(os.path.join(base, "Dockerfile"))))
    results.append(check("docker-compose.yml exists",
                         os.path.exists(os.path.join(base, "docker-compose.yml"))))
    results.append(check(".dockerignore exists",
                         os.path.exists(os.path.join(base, ".dockerignore"))))
    results.append(check("requirements.txt exists",
                         os.path.exists(os.path.join(base, "requirements.txt"))))

    # -- Security --------------------------------------
    print("\n[Security] Protection")
    
    secrets_found = []
    for f in ["app/main.py", "app/config.py"]:
        fpath = os.path.join(base, f)
        if os.path.exists(fpath):
            with open(fpath, encoding='utf-8') as file:
                content = file.read()
                for bad in ["sk-", "password123"]:
                    if bad in content:
                        secrets_found.append(f"{f}:{bad}")
    results.append(check("No hardcoded secrets in code",
                         len(secrets_found) == 0,
                         str(secrets_found) if secrets_found else ""))

    # -- API Endpoints ---------------------------------
    print("\n[API] Features")
    main_py = os.path.join(base, "app", "main.py")
    if os.path.exists(main_py):
        with open(main_py, encoding='utf-8') as file:
            content = file.read()
            results.append(check("/health endpoint defined", '"/health"' in content))
            results.append(check("/ready endpoint defined", '"/ready"' in content))
            results.append(check("Authentication implemented", "verify_api_key" in content))
            results.append(check("Rate limiting implemented", "check_rate_limit" in content))
            results.append(check("Cost guard implemented", "check_budget" in content))
            results.append(check("Stateless logic (Redis history)", "rpush" in content or "lrange" in content))
            results.append(check("Structured logging", "json.dumps" in content))
    else:
        results.append(check("app/main.py exists", False))

    # -- Docker ----------------------------------------
    print("\n[Docker] Containerization")
    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        with open(dockerfile, encoding='utf-8') as file:
            content = file.read()
            results.append(check("Multi-stage build", "AS builder" in content and "AS runtime" in content))
            results.append(check("Non-root user", "USER " in content))
            results.append(check("HEALTHCHECK instruction", "HEALTHCHECK" in content))

    # -- Summary ---------------------------------------
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = round(passed / total * 100)

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")

    if pct == 100:
        print("  CONGRATULATIONS! Your Lab 6 project is PRODUCTION READY!")
    else:
        print("  Almost there! Fix the [FAIL] items above.")
    print("=" * 55 + "\n")
    return pct == 100

if __name__ == "__main__":
    run_checks()
