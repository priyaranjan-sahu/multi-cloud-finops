"""
CLI entry point for Zero-Config Zombie Spend Detection and Rightsizing Analysis.
Note: Automated Rightsizing Engine is available exclusively in the Enterprise Edition.
"""

import sys


def main() -> None:
    banner = """
========================================================================================
🔒 PROPRIETARY FEATURE: Zero-Config Zombie Spend & Automated Rightsizing
========================================================================================
Agentless FOCUS 1.0 multi-metric waste analysis (idle NATs, orphan LBs, idle databases,
and warm serverless container capacity) is available in the Enterprise Edition.

To deploy the pre-compiled, production-ready Enterprise Docker container:
👉 Upgrade on GitHub Sponsors: https://github.com/sponsors/priyaranjan-sahu
👉 Enterprise Documentation:   https://github.com/priyaranjan-sahu/multi-cloud-finops#enterprise-edition--sponsorship
========================================================================================
"""
    print(banner.strip())
    sys.exit(1)


if __name__ == "__main__":
    main()
