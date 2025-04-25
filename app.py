from flask import Flask, render_template, request, send_file, url_for
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Robot code template
ROBOT_CODE_TEMPLATE = """from robot_command.rpl import *
import math

set_units("mm", "deg")

def main():
    # Example initial move
    movej(j[0,0,0,0,0,0], velocity_scale=0.2)

    # Example user frame
    userFrame_pos_x = 400
    userFrame_pos_y = 0
    userFrame_pos_z = 550
    userFrame_rotation_A = 0
    userFrame_rotation_B = 0
    userFrame_rotation_C = 0
    set_user_frame("user_frame1",
                   position=p[userFrame_pos_x,
                              userFrame_pos_y,
                              userFrame_pos_z,
                              userFrame_rotation_A,
                              userFrame_rotation_B,
                              userFrame_rotation_C])
    change_user_frame("user_frame1")

    # Auto-generated move commands:
{moves}

    exit()
"""

# Keep track of the last generated file name.
# In a multi-user setting, you'd want a more robust approach (e.g., session, database, or random IDs).
GENERATED_FILENAME = ""

@app.route("/", methods=["GET", "POST"])
def index():
    global GENERATED_FILENAME

    if request.method == "POST":
        # Make sure a file was actually uploaded
        if "file" not in request.files:
            return "No file part"

        file = request.files["file"]
        if file.filename == "":
            return "No selected file"

        # Save uploaded CSV
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Read CSV into pandas
        df = pd.read_csv(filepath)

        # Choose your skipping logic:
        # E.g., every 150th row:
        df = df.iloc[::150]

        # Or if you prefer every 500th row:
        # df = df.iloc[::500]

        # Build 'movej' commands from the columns in the DataFrame
        # Assuming 6 columns: X, Y, Z, A, B, C
        move_commands = []
        for _, row in df.iterrows():
            x_val = row[0]
            y_val = row[1]
            z_val = row[2]
            a_val = row[3]
            b_val = row[4]
            c_val = row[5]
            cmd = f"    movej(p[{x_val}, {y_val}, {z_val}, {a_val}, {b_val}, {c_val}], velocity_scale=0.2)"
            move_commands.append(cmd)

        # Join them into one block of text
        moves_block = "\n".join(move_commands)
        final_code = ROBOT_CODE_TEMPLATE.format(moves=moves_block)

        # Generate a unique file name (to avoid collisions on multi uploads)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        GENERATED_FILENAME = f"robot_path_{timestamp_str}.py"

        # Write the code to the file
        with open(GENERATED_FILENAME, "w", encoding="utf-8") as f:
            f.write(final_code)

        # Create a small HTML table preview for the user (show up to 10 rows)
        # If your CSV is huge, you might limit or skip this step.
        df_preview_html = df.head(10).to_html(index=False)

        # Render the template: show a success message, a link to download, and a preview
        return render_template(
            "index.html",
            table_html=df_preview_html,
            file_ready=True
        )

    # If GET request, just show the page
    return render_template("index.html", file_ready=False)

@app.route("/download_robot_code")
def download_robot_code():
    # Send the previously generated file
    if os.path.exists(GENERATED_FILENAME):
        return send_file(GENERATED_FILENAME, as_attachment=True)
    else:
        return "No generated file found!"

if __name__ == "__main__":
    app.run(debug=True)
