import streamlit as st
import google.generativeai as genai
import os
import json
import re
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the app
st.set_page_config(
    page_title="🍳 Free Recipe AI",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cache the Gemini model to avoid reinitialization
@st.cache_resource
def setup_gemini():
    """Initialize Gemini AI with free API"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("🚫 API Key Missing!")
        st.info("""
        **How to get your FREE Gemini API key:**
        1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Sign in with your Google account
        3. Click "Create API Key"
        4. Copy the key and add it to your `.env` file as:
           `GEMINI_API_KEY=your_free_key_here`
        """)
        return None
    
    try:
        genai.configure(api_key=api_key)
        
        # Use the correct model name - gemini-2.0-flash is free and fast
        return genai.GenerativeModel('gemini-2.0-flash')
        
    except Exception as e:
        st.error(f"❌ Setup failed: {str(e)}")
        return None

def safe_ai_request(model, prompt, max_retries=2):
    """Make safe API requests with retries and rate limiting"""
    for attempt in range(max_retries):
        try:
            # Add delay to respect rate limits
            if attempt > 0:
                time.sleep(1)
            
            response = model.generate_content(prompt)
            return response
            
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                wait_time = (attempt + 1) * 3
                st.warning(f"⏳ Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                st.error(f"API Error: {error_msg}")
                return None
    return None

def get_smart_recipes(ingredients_list, model):
    """Get recipe suggestions optimized for free API"""
    try:
        # Efficient prompt for free tier
        prompt = f"""
        Create 2-3 simple, practical recipes using primarily these ingredients: {', '.join(ingredients_list)}
        
        For each recipe, provide brief but useful information in this EXACT JSON format:
        {{
            "recipes": [
                {{
                    "name": "Recipe Name",
                    "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
                    "steps": ["Step 1 instruction", "Step 2 instruction", "Step 3 instruction"],
                    "time": "15-20 mins",
                    "effort": "Easy"
                }}
            ]
        }}
        
        Important:
        - Focus on recipes that actually work with these ingredients
        - Keep steps simple and practical (2-3 steps max)
        - Use maximum 2-3 additional common pantry ingredients
        - Return ONLY valid JSON, no other text or explanations
        - Make sure the JSON is properly formatted and parseable
        """
        
        response = safe_ai_request(model, prompt)
        if not response:
            return get_fallback_recipes(ingredients_list)
            
        response_text = response.text.strip()
        
        # Clean response - remove markdown code blocks
        response_text = re.sub(r'```json\s*|\s*```', '', response_text)
        
        # Try to parse JSON
        try:
            data = json.loads(response_text)
            recipes = data.get("recipes", [])
            if recipes:
                return recipes
            else:
                return get_fallback_recipes(ingredients_list)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return data.get("recipes", get_fallback_recipes(ingredients_list))
                except:
                    return get_fallback_recipes(ingredients_list)
            else:
                return get_fallback_recipes(ingredients_list)
        
    except Exception as e:
        st.error(f"Recipe generation failed: {str(e)}")
        return get_fallback_recipes(ingredients_list)

def get_fallback_recipes(ingredients_list):
    """Provide fallback recipes if AI fails"""
    # Filter ingredients to usable ones
    usable_ings = [ing for ing in ingredients_list if len(ing) > 2]
    
    fallbacks = []
    
    # Recipe 1: Stir fry if we have vegetables/protein
    if any(ing in ' '.join(usable_ings) for ing in ['chicken', 'beef', 'tofu', 'vegetable', 'broccoli', 'carrot']):
        fallbacks.append({
            "name": "Quick Stir Fry",
            "ingredients": usable_ings[:4] + ["soy sauce", "cooking oil", "garlic"],
            "steps": [
                "Heat oil in a pan and sauté garlic until fragrant",
                "Add main ingredients and stir fry for 5-7 minutes",
                "Add soy sauce and any seasonings, cook for 2 more minutes"
            ],
            "time": "15 mins",
            "effort": "Easy"
        })
    
    # Recipe 2: Salad if we have fresh ingredients
    fresh_ings = [ing for ing in usable_ings if any(x in ing for x in ['lettuce', 'tomato', 'cucumber', 'onion', 'spinach'])]
    if len(fresh_ings) >= 2:
        fallbacks.append({
            "name": "Fresh Salad",
            "ingredients": fresh_ings + ["olive oil", "vinegar or lemon juice", "salt", "pepper"],
            "steps": [
                "Wash and chop all vegetables",
                "Mix with olive oil and vinegar/lemon juice",
                "Season with salt and pepper to taste"
            ],
            "time": "10 mins",
            "effort": "Very Easy"
        })
    
    # Recipe 3: Pasta dish if we have pasta or noodles
    if any(ing in ' '.join(usable_ings) for ing in ['pasta', 'noodle', 'spaghetti']):
        fallbacks.append({
            "name": "Simple Pasta",
            "ingredients": [ing for ing in usable_ings if 'pasta' in ing or 'noodle' in ing] + ["oil", "garlic", "herbs"] + usable_ings[:2],
            "steps": [
                "Cook pasta according to package instructions",
                "Sauté other ingredients in oil with garlic",
                "Combine with cooked pasta and season"
            ],
            "time": "20 mins",
            "effort": "Easy"
        })
    
    # If no specific matches, create a general recipe
    if not fallbacks and len(usable_ings) >= 3:
        fallbacks.append({
            "name": "Simple Cooked Dish",
            "ingredients": usable_ings[:5] + ["oil", "salt", "pepper"],
            "steps": [
                "Prepare and chop all ingredients",
                "Cook in oil until tender and flavorful",
                "Season with salt and pepper, serve hot"
            ],
            "time": "20 mins",
            "effort": "Easy"
        })
    
    return fallbacks[:3]  # Return max 3 fallback recipes

def main():
    st.title("🍳 Free Recipe AI Assistant")
    st.markdown("### ♻️ Cook Smart, Reduce Waste - **100% Free!**")
    
    # Initialize Gemini (free version)
    model = setup_gemini()
    
    # Sidebar
    with st.sidebar:
        st.header("🛒 Your Ingredients")
        ingredients_input = st.text_area(
            "What's in your kitchen?",
            placeholder="chicken, rice, tomatoes, onion, garlic, eggs, flour, pasta...",
            height=120,
            help="Separate with commas. Include staples like oil, salt, spices."
        )
        
        st.header("⚙️ Options")
        use_ai = st.toggle("Enable AI Recipes", value=True, help="Uses free Gemini API")
        
        if st.button("🚀 Find Recipes!", type="primary", use_container_width=True):
            if ingredients_input and len(ingredients_input.strip()) > 3:
                st.session_state.search_clicked = True
                st.session_state.ingredients = ingredients_input
            else:
                st.warning("Please enter at least 2-3 ingredients")
        
        # Quick ingredient examples
        st.header("🍽️ Quick Examples")
        examples = {
            "Chicken Dinner": "chicken, rice, broccoli, garlic, soy sauce, onion, carrot",
            "Pasta Night": "pasta, tomato, basil, garlic, olive oil, cheese, onion",
            "Breakfast": "eggs, flour, milk, butter, sugar, baking powder",
            "Vegetarian": "potato, onion, bell pepper, beans, rice, spices"
        }
        
        for name, ings in examples.items():
            if st.button(f"{name}", use_container_width=True, key=name):
                st.session_state.ingredients = ings
                st.session_state.search_clicked = True
                st.rerun()
    
    # Main content
    if hasattr(st.session_state, 'search_clicked') and st.session_state.search_clicked:
        ingredients_text = st.session_state.ingredients
        ingredients_list = [ing.strip().lower() for ing in ingredients_text.split(',') if ing.strip()]
        
        st.success(f"🎯 Found **{len(ingredients_list)}** ingredients to work with!")
        st.write(f"**Your ingredients:** {', '.join(ingredients_list)}")
        
        if use_ai and model:
            with st.spinner("🤖 Free AI Chef is cooking up recipes..."):
                recipes = get_smart_recipes(ingredients_list, model)
            
            if recipes:
                st.subheader("🍽️ Your Custom Recipes")
                
                for i, recipe in enumerate(recipes, 1):
                    with st.container():
                        # Recipe header
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(f"### {i}. {recipe.get('name', 'Quick Meal')}")
                        with col_b:
                            st.metric("⏱️ Time", recipe.get('time', 'N/A'))
                            st.metric("📊 Effort", recipe.get('effort', 'Easy'))
                        
                        # Ingredients
                        st.markdown("**📋 Ingredients:**")
                        user_ings = []
                        other_ings = []
                        
                        for ingredient in recipe.get('ingredients', []):
                            ing_lower = ingredient.lower()
                            if any(user_ing in ing_lower for user_ing in ingredients_list):
                                user_ings.append(f"✅ {ingredient}")
                            else:
                                other_ings.append(f"▪️ {ingredient}")
                        
                        # Display in columns if we have both types
                        if user_ings and other_ings:
                            ing_cols = st.columns(2)
                            with ing_cols[0]:
                                st.markdown("**What you have:**")
                                for ing in user_ings:
                                    st.write(ing)
                            with ing_cols[1]:
                                st.markdown("**You might need:**")
                                for ing in other_ings:
                                    st.write(ing)
                        else:
                            for ing in user_ings + other_ings:
                                st.write(ing)
                        
                        # Instructions
                        with st.expander("📝 Cooking Instructions"):
                            for step_num, step in enumerate(recipe.get('steps', []), 1):
                                st.write(f"{step_num}. {step}")
                        
                        st.markdown("---")
            
            else:
                st.error("❌ Could not generate recipes. Please try with different ingredients.")
        
        elif not use_ai:
            st.info("🔒 Enable 'AI Recipes' for smart suggestions using free Gemini API!")
    
    else:
        # Welcome screen
        st.markdown("""
        ## 🎯 Welcome to Your Free Recipe Assistant!
        
        **✨ Perfect for:**
        - 🏠 **Home cooks** on a budget
        - 👨‍🎓 **Students** with limited ingredients  
        - ♻️ **Eco-conscious** cooks reducing waste
        - 🕒 **Busy people** who need quick ideas
        
        ### 🚀 **How to start:**
        1. **Enter your ingredients** in the sidebar
        2. **Click "Find Recipes!"** 
        3. **Get AI-powered recipe suggestions** instantly!
        
        **🍽️ Try the quick examples in the sidebar to see how it works!**
        """)

if __name__ == "__main__":
    main()