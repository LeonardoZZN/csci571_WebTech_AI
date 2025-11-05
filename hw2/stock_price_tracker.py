import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Page configuration
st.set_page_config(
    page_title="Stock Price Tracker",
    page_icon="📈",
    layout="wide"
)

# Title and description
st.title("📈 7-Day Stock Price Tracker")
st.markdown("Enter a stock symbol to view the 7-day price chart and current information.")

# API configuration
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "demo")
BASE_URL = "https://api.twelvedata.com"

def fetch_stock_data(symbol):
    """
    Fetch 7-day stock data from Twelve Data API
    """
    try:
        # Calculate date range for 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # Get a few extra days to ensure we have 7 trading days
        
        # Format dates for API
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # API endpoint for time series data
        url = f"{BASE_URL}/time_series"
        params = {
            "symbol": symbol.upper(),
            "interval": "1day",
            "start_date": start_date_str,
            "end_date": end_date_str,
            "apikey": API_KEY,
            "format": "JSON"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if "status" in data and data["status"] == "error":
            return None, data.get("message", "API returned an error")
        
        if "values" not in data or not data["values"]:
            return None, f"No data found for symbol {symbol}. Please check if the symbol is valid."
        
        # Convert to DataFrame
        df = pd.DataFrame(data["values"])
        
        # Convert datetime and numeric columns
        df["datetime"] = pd.to_datetime(df["datetime"])
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Sort by date (oldest first)
        df = df.sort_values("datetime")
        
        # Keep only last 7 days of data
        df = df.tail(7)
        
        return df, None
        
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Error processing data: {str(e)}"

def fetch_current_quote(symbol):
    """
    Fetch current stock quote for additional information
    """
    try:
        url = f"{BASE_URL}/quote"
        params = {
            "symbol": symbol.upper(),
            "apikey": API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "status" in data and data["status"] == "error":
            return None
            
        return data
        
    except:
        return None

def create_price_chart(df, symbol):
    """
    Create an interactive price chart using Plotly
    """
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name=f"{symbol.upper()} Price",
        increasing_line_color="green",
        decreasing_line_color="red"
    ))
    
    # Update layout
    fig.update_layout(
        title=f"{symbol.upper()} - 7-Day Price Chart",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=500,
        showlegend=False
    )
    
    return fig

def display_stock_info(quote_data, df):
    """
    Display current stock information in columns
    """
    if quote_data and df is not None:
        col1, col2, col3, col4 = st.columns(4)
        
        # Current price
        current_price = quote_data.get("close")
        if current_price:
            col1.metric("Current Price", f"${float(current_price):.2f}")
        
        # Daily change
        change = quote_data.get("change")
        percent_change = quote_data.get("percent_change")
        if change and percent_change:
            col2.metric(
                "Daily Change", 
                f"${float(change):.2f}",
                f"{float(percent_change):.2f}%"
            )
        
        # 7-day range
        if not df.empty:
            week_high = df["high"].max()
            week_low = df["low"].min()
            col3.metric("7-Day High", f"${week_high:.2f}")
            col4.metric("7-Day Low", f"${week_low:.2f}")

# Main application
def main():
    # Input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        symbol = st.text_input(
            "Enter Stock Symbol",
            placeholder="e.g., AAPL, GOOGL, TSLA",
            help="Enter a valid stock symbol to view the 7-day price chart"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing
        search_button = st.button("Get Stock Data", type="primary")
    
    # Process when symbol is entered or button is clicked
    if symbol and (search_button or symbol):
        symbol = symbol.strip().upper()
        
        if len(symbol) < 1 or len(symbol) > 10:
            st.error("Please enter a valid stock symbol (1-10 characters)")
            return
        
        # Show loading spinner
        with st.spinner(f"Fetching data for {symbol}..."):
            # Fetch stock data
            df, error = fetch_stock_data(symbol)
            quote_data = fetch_current_quote(symbol)
        
        if error:
            st.error(f"❌ {error}")
            st.info("💡 **Tip**: Make sure you're using a valid stock symbol (e.g., AAPL for Apple, GOOGL for Google)")
            return
        
        if df is None or df.empty:
            st.error(f"No data available for {symbol}. Please check the symbol and try again.")
            return
        
        # Display success message
        st.success(f"✅ Successfully loaded data for {symbol}")
        
        # Display current stock information
        display_stock_info(quote_data, df)
        
        # Display the chart
        st.subheader(f"📊 {symbol} - 7-Day Price Chart")
        chart = create_price_chart(df, symbol)
        st.plotly_chart(chart, use_container_width=True)
        
        # Display data table
        with st.expander("📋 View Raw Data"):
            # Format the dataframe for display
            display_df = df.copy()
            display_df["Date"] = display_df["datetime"].dt.strftime("%Y-%m-%d")
            display_df = display_df[["Date", "open", "high", "low", "close", "volume"]]
            display_df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
            
            # Format numeric columns
            for col in ["Open", "High", "Low", "Close"]:
                display_df[col] = display_df[col].apply(lambda x: f"${x:.2f}")
            display_df["Volume"] = display_df["Volume"].apply(lambda x: f"{x:,.0f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Instructions
    if not symbol:
        st.info("👆 Enter a stock symbol above to get started")
        
        # Example symbols
        st.markdown("### 💡 Popular Stock Symbols")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **Technology:**
            - AAPL (Apple)
            - GOOGL (Google)
            - MSFT (Microsoft)
            - TSLA (Tesla)
            """)
        
        with col2:
            st.markdown("""
            **Finance:**
            - JPM (JPMorgan)
            - BAC (Bank of America)
            - WFC (Wells Fargo)
            - GS (Goldman Sachs)
            """)
        
        with col3:
            st.markdown("""
            **Other:**
            - AMZN (Amazon)
            - NFLX (Netflix)
            - NVDA (NVIDIA)
            - META (Meta)
            """)

# Footer
def show_footer():
    st.markdown("---")
    st.markdown(
        "📈 **Stock Price Tracker** | Data provided by [Twelve Data](https://twelvedata.com/) | "
        "⚠️ *This is for informational purposes only and should not be considered as financial advice*"
    )

if __name__ == "__main__":
    main()
    show_footer()
