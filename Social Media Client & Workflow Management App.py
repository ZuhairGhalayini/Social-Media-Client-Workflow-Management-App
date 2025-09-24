import instaloader
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime

# Initialize Instaloader
L = instaloader.Instaloader()

def generate_report(username):
    profile = instaloader.Profile.from_username(L.context, username)

    # Basic info
    followers = profile.followers
    following = profile.followees
    posts_count = profile.mediacount

    print(f"📊 {username}")
    print(f"Followers: {followers}")
    print(f"Following: {following}")
    print(f"Posts: {posts_count}")

    # Collect engagement (likes on latest 10 posts)
    likes_list = []
    captions = []
    for post in profile.get_posts():
        likes_list.append(post.likes)
        captions.append(post.caption[:30] if post.caption else "")
        if len(likes_list) == 10:
            break

    # === PDF Report ===
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, f"Instagram Report - {username}", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Date: {datetime.today().strftime('%Y-%m-%d')}", ln=True)
    pdf.cell(200, 10, f"Followers: {followers}", ln=True)
    pdf.cell(200, 10, f"Following: {following}", ln=True)
    pdf.cell(200, 10, f"Total Posts: {posts_count}", ln=True)

    # Plot likes chart
    plt.figure()
    plt.bar(range(1, len(likes_list)+1), likes_list)
    plt.title("Likes on Recent Posts")
    plt.xlabel("Post #")
    plt.ylabel("Likes")
    chart_path = f"{username}_likes.png"
    plt.savefig(chart_path)
    plt.close()

    pdf.image(chart_path, x=10, w=180)

    # Save PDF
    filename = f"{username}_report.pdf"
    pdf.output(filename)
    print(f"✅ Report saved as {filename}")

# Example usage
generate_report("cristiano")  # replace with client username
