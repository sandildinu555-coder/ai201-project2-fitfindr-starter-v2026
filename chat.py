import config  # sets UTF-8 console encoding on Windows
from agent import run_agent
from utils.data_loader import get_example_wardrobe


def main() -> None:
    wardrobe = get_example_wardrobe()
    pending_query = ""

    print("=" * 60)
    print("  FitFindr Interactive Chat  (type 'reset' or 'quit')")
    print("=" * 60)

    while True:
        try:
            prompt_label = "You (follow-up): " if pending_query else "You: "
            user_input = input(f"\n{prompt_label}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input or user_input.lower() in {"quit", "exit"}:
            print("Bye!")
            break

        if user_input.lower() == "reset":
            pending_query = ""
            print("FitFindr: Conversation cleared. What are you looking for?")
            continue

        # Combine follow-up answers with the original incomplete query
        full_query = f"{pending_query} {user_input}".strip() if pending_query else user_input

        print("-" * 60)
        session = run_agent(full_query, wardrobe)
        print("-" * 60)

        # Gatekeeper blocked: keep the partial query and wait for the user's answer
        if session.get("missing_fields"):
            pending_query = full_query
            print(f"\nFitFindr: {session['error']}")
            continue

        # Search ran (either matched or 0 matches): reset for the next request
        pending_query = ""

        if session.get("error"):
            print(f"\nFitFindr: {session['error']}")
        else:
            item = session.get("selected_item") or {}
            brand = item.get("brand") or "unbranded"
            print(f"\nFitFindr found: {item.get('title')} (brand: {brand}) — ${item.get('price')} on {item.get('platform')}")
            print(f"\nOutfit:\n  {session['outfit_suggestion']}")
            print(f"\nFit Card:\n  {session['fit_card']}")


if __name__ == "__main__":
    main()