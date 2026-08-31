"""
CLI entry point for Exporting Rightsizing and Waste Recommendations.
Note: Automated recommendation exports are available in the Enterprise Edition.
"""

import sys


def main() -> None:
    banner = """
========================================================================================
🔒 PROPRIETARY FEATURE: Automated Rightsizing Recommendation Exporter
========================================================================================
Export automated multi-cloud waste reduction plans in CSV/JSON format using the
Enterprise Edition pre-compiled Docker container.

To deploy the pre-compiled, production-ready Enterprise Docker container:
👉 Upgrade on GitHub Sponsors: https://github.com/sponsors/priyaranjan-sahu
👉 Enterprise Documentation:   https://github.com/priyaranjan-sahu/multi-cloud-finops#enterprise-edition--sponsorship
========================================================================================
"""
    print(banner.strip())
    sys.exit(1)


if __name__ == "__main__":
    main()
