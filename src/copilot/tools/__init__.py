"""Tools the agent can call. Each returns plain JSON-serializable data.

Design rule: anything safety- or compliance-critical (hazmat segregation, carrier
eligibility, departure risk) is decided by deterministic, tested code here. The LLM
chooses which tool to call and explains the result - it never makes those calls itself.
"""
