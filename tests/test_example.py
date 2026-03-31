"""
Example test file demonstrating testing patterns
"""
import pytest
from hypothesis import given, strategies as st


@pytest.mark.unit
def test_example_unit():
    """Example unit test."""
    assert 1 + 1 == 2


@pytest.mark.unit
def test_sample_user_data(sample_user_data):
    """Test using fixture."""
    assert sample_user_data["phone_number"] == "+8613800138000"
    assert sample_user_data["identity"] == "student"


@pytest.mark.property
@given(amount=st.floats(min_value=0.01, max_value=10000.0))
def test_expense_amount_property(amount):
    """
    Example property-based test.
    Feature: mobile-ai-finance-assistant, Property: Expense amounts should be positive
    """
    # Property: All expense amounts should be positive
    assert amount > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_example_integration(client):
    """Example integration test with test client."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.slow
def test_example_slow():
    """Example slow test that can be skipped."""
    import time
    time.sleep(0.1)
    assert True
