"""
CLI entry point for Zero-Config Zombie Spend Detection and Rightsizing Analysis.
Note: Automated Rightsizing Engine is available exclusively in the Enterprise Edition.
"""

import sys


def main() -> None:
    banner = """
========================================================================================
🔒 PROPRIETARY FEATURE: Zero-Config Zombie Spend & Warm Uptime Trap Detection
========================================================================================
Agentless FOCUS 1.0 Bi-Modal Activity Density analysis:
• Detects pure zombies (0.0 requests, 0 MB transfer).
• Catches 720h warm serverless containers (Cloud Run, Fargate) billing 24/7 flat uptime
  while serving only synthetic healthchecks (< 2 req/hr, < 50KB payload).
• Automated compute downscaling, spot migration, and reservation coverage.

To deploy the pre-compiled, production-ready Enterprise Docker container:
👉 Upgrade on GitHub Sponsors: https://github.com/sponsors/priyaranjan-sahu
👉 Enterprise Documentation:   https://github.com/priyaranjan-sahu/multi-cloud-finops#enterprise-edition--sponsorship
========================================================================================
"""
    print(banner.strip())
    sys.exit(1)


if __name__ == "__main__":
    main()
