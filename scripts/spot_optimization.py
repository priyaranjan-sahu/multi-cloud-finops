"""
CLI entry point for Spot and Preemptible Capacity Migration Analysis.
Note: Spot Capacity Migration Heuristics are available in the Enterprise Edition.
"""

import sys


def main() -> None:
    banner = """
========================================================================================
🔒 PROPRIETARY FEATURE: Spot / Preemptible Capacity Migration Engine
========================================================================================
Automated spot candidate qualification and multi-cloud discount simulation are
available in the Enterprise Edition pre-compiled Docker container.

To deploy the pre-compiled, production-ready Enterprise Docker container:
👉 Upgrade on GitHub Sponsors: https://github.com/sponsors/priyaranjan-sahu
👉 Enterprise Documentation:   https://github.com/priyaranjan-sahu/multi-cloud-finops#enterprise-edition--sponsorship
========================================================================================
"""
    print(banner.strip())
    sys.exit(1)


if __name__ == "__main__":
    main()
