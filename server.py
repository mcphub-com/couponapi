import os
import requests
from typing import Union, Literal, List, Annotated, Optional
from dotenv import load_dotenv
from pydantic import Field
from mcp.server import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP instance
mcp = FastMCP('coupon-feed-server')

# API configuration
COUPON_API_URL = "https://couponapi.org/api/getIncrementalFeed/"
COUPON_API_KEY = os.getenv("COUPON_API_KEY")

@mcp.tool()
def get_incremental_feed(
    last_extract: Annotated[Optional[int], Field(description="Last extract timestamp as UNIX timestamp in seconds (epoch). If not provided, returns all active offers.")] = None,
    response_format: Annotated[Optional[Literal['json', 'csv']], Field(description="Response format: 'json' or 'csv'. Defaults to 'json'.")] = 'json',
    limit: Annotated[Optional[int], Field(description="Maximum number of offers to return. Optional parameter.")] = None,
    store_id: Annotated[Optional[str], Field(description="Filter by specific store ID. Optional parameter.")] = None,
    category: Annotated[Optional[str], Field(description="Filter by category. Optional parameter.")] = None,
    off_record: Annotated[Optional[bool], Field(description="When True, does not update the last extract time, allowing repeated retrieval of incremental data. Defaults to False.")] = False
):
    """Get incremental feed of coupon offers from CouponAPI.org
    
    Returns new, updated, and suspended offers since the last extract time.
    If no last_extract is provided, returns all currently active offers.
    Set off_record=True to avoid updating the last extract time in the system.
    """
    
    if not COUPON_API_KEY:
        raise ValueError("COUPON_API_KEY environment variable is required")
    
    # Build request parameters
    params = {
        'API_KEY': COUPON_API_KEY,
        'format': response_format
    }
    
    # Add optional parameters if provided
    if last_extract:
        params['last_extract'] = last_extract
    if limit:
        params['limit'] = limit
    if store_id:
        params['store_id'] = store_id
    if category:
        params['category'] = category
    if off_record:
        params['off_record'] = '1'
    
    try:
        # Make API request
        response = requests.get(COUPON_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        # Return JSON response or raw text for CSV
        if response_format == 'json':
            return response.json()
        else:
            return {"data": response.text, "format": "csv"}
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing coupon feed: {str(e)}")

@mcp.tool()
def get_offer_details(
    offer_id: Annotated[str, Field(description="The unique offer ID to get details for")]
):
    """Get detailed information for a specific offer
    
    This tool filters the incremental feed to return details for a specific offer ID.
    """
    
    # Get all offers and filter by offer_id
    feed_data = get_incremental_feed()
    
    if 'offers' not in feed_data:
        return {"error": "No offers found in feed"}
    
    # Find the specific offer
    for offer in feed_data['offers']:
        if offer.get('offer_id') == offer_id:
            return offer
    
    return {"error": f"Offer with ID {offer_id} not found"}

@mcp.tool()
def get_offers_by_store(
    store_name: Annotated[str, Field(description="Store name to filter offers by")]
):
    """Get all offers for a specific store
    
    Returns all current offers for the specified store name.
    """
    
    # Get all offers
    feed_data = get_incremental_feed()
    
    if 'offers' not in feed_data:
        return {"error": "No offers found in feed"}
    
    # Filter by store name (case-insensitive)
    store_offers = []
    for offer in feed_data['offers']:
        if offer.get('store_name', '').lower() == store_name.lower():
            store_offers.append(offer)
    
    return {
        "store_name": store_name,
        "offer_count": len(store_offers),
        "offers": store_offers
    }

@mcp.tool()
def get_offers_by_category(
    category: Annotated[str, Field(description="Category to filter offers by")]
):
    """Get all offers for a specific category
    
    Returns all current offers for the specified category.
    """
    
    # Get all offers
    feed_data = get_incremental_feed()
    
    if 'offers' not in feed_data:
        return {"error": "No offers found in feed"}
    
    # Filter by category (case-insensitive)
    category_offers = []
    for offer in feed_data['offers']:
        offer_categories = offer.get('categories', [])
        if isinstance(offer_categories, list):
            if any(cat.lower() == category.lower() for cat in offer_categories):
                category_offers.append(offer)
        elif isinstance(offer_categories, str):
            if category.lower() in offer_categories.lower():
                category_offers.append(offer)
    
    return {
        "category": category,
        "offer_count": len(category_offers),
        "offers": category_offers
    }

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9998
    mcp.run(transport="stdio")