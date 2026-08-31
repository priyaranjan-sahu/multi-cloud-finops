"""
CLI entry point for Change Intelligence and Deployment Cost Attribution.
Note: Deployment-to-Cost Attribution is available exclusively in the Enterprise Edition.
"""

import sys


def main() -> None:
    banner = """
========================================================================================
🔒 PROPRIETARY FEATURE: Change Intelligence & Deployment-to-Cost Attribution
========================================================================================
Correlate multi-cloud billing baseline shifts directly to Git commit SHAs, authors,
and configuration diffs using the Enterprise Edition.

To deploy the pre-compiled, production-ready Enterprise Docker container:
👉 Upgrade on GitHub Sponsors: https://github.com/sponsors/priyaranjan-sahu
👉 Enterprise Documentation:   https://github.com/priyaranjan-sahu/multi-cloud-finops#enterprise-edition--sponsorship
========================================================================================
"""
    print(banner.strip())
    sys.exit(1)


if __name__ == "__main__":
    main()
