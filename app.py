from cs50 import SQL
from flask import Flask, jsonify, render_template, redirect, request
from distutils.log import debug
from fileinput import filename
import docx2txt
import os
import jinja2
import json

app = Flask(__name__)

db = SQL("sqlite:///dic.db")

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/delete", methods=["POST"])
def delete():
    # delete from db.
    id = request.form.get("id")
    id_prelim = request.form.get("id_prelim")
    idAll = request.form.get("idAll")
    if id:
        db.execute("DELETE FROM dictionary WHERE id=?", id)
        return redirect("/")
    if id_prelim:
        db.execute("DELETE FROM prelim WHERE id=?", id_prelim)
        prelim = db.execute("SELECT * FROM prelim")
        return render_template("upload.html", prelim=prelim)
    if idAll:
        db.execute("DELETE FROM prelim")
        return redirect('/upload')


@app.route("/modify", methods=["POST"])
def modify():
    id = request.form.get("id")
    if id:
        dic = db.execute("SELECT * FROM dictionary WHERE id=?", id)
        return render_template("modify.html", dic=dic)

    id2 = request.form.get("id2")
    tm = request.form.get("tm")
    fr = request.form.get("fr")
    ru = request.form.get("ru")
    if id2:
        db.execute(
            "UPDATE dictionary SET tm = ?, fr = ?, ru = ? WHERE id = ?", tm, fr, ru, id2)
        return render_template("succes.html")

    id_prelim = request.form.get("id_prelim")
    if id_prelim:
        prelimdic = db.execute("SELECT * FROM prelim WHERE id=?", id_prelim)
        return render_template("modify.html", prelimdic=prelimdic)

    idprelim2 = request.form.get("idprelim2")
    tmpr = request.form.get("tmpr")
    frpr = request.form.get("frpr")
    rupr = request.form.get("rupr")
    if idprelim2:
        db.execute(
            "UPDATE prelim SET tm = ?, fr = ?, ru = ? WHERE id = ?", tmpr, frpr, rupr, idprelim2)
        return redirect("/upload")


@app.route("/shift", methods=["POST"])
def shift():
    if request.method == "POST":
        tm = request.form.get("tm")
        fr = request.form.get("fr")
        ru = request.form.get("ru")
        id = request.form.get("id")
        id_next = db.execute("SELECT id FROM prelim WHERE id > ? LIMIT 1", id)
        last_id = db.execute("SELECT MAX(id) FROM prelim")

        if id == last_id[0]["MAX(id)"]:
            return apology("You cant move the last item", 400)

        if tm:
            tm_next = db.execute(
                "SELECT tm FROM prelim WHERE id=?", id_next[0]["id"])
            db.execute("UPDATE prelim SET tm = ? WHERE id=? ",
                       tm_next[0]["tm"], id)
            db.execute("UPDATE prelim SET tm = ? WHERE id=? ",
                       tm, id_next[0]["id"])
            return redirect("/upload")

        if fr:
            fr_next = db.execute(
                "SELECT fr FROM prelim WHERE id=?", id_next[0]["id"])
            db.execute("UPDATE prelim SET fr = ? WHERE id=? ",
                       fr_next[0]["fr"], id)
            db.execute("UPDATE prelim SET fr = ? WHERE id=? ",
                       fr, id_next[0]["id"])
            return redirect("/upload")
        if ru:
            ru_next = db.execute(
                "SELECT ru FROM prelim WHERE id=?", id_next[0]["id"])
            db.execute("UPDATE prelim SET ru = ? WHERE id=? ",
                       ru_next[0]["ru"], id)
            db.execute("UPDATE prelim SET ru = ? WHERE id=? ",
                       ru, id_next[0]["id"])
            return redirect("/upload")
        # if tm:
        #     tm_date = db.execute("SELECT tm FROM prelim where id > ?", id)
        #     db.execute("SELECT tm_date INTO prelim FROM prelim WHERE id", tm)


@app.route("/input", methods=["GET", "POST"])
def input():

    if request.method == "POST":
        id = request.form.get("id")
        tm = request.form.get("tm")
        fr = request.form.get("fr")
        ru = request.form.get("ru")

        tm_ex = db.execute("SELECT tm FROM dictionary WHERE tm=?", tm)
        fr_ex = db.execute("SELECT fr FROM dictionary WHERE fr=?", fr)
        ru_ex = db.execute("SELECT ru FROM dictionary WHERE ru=?", ru)

        if not (tm and fr) or not (tm and ru) or not (ru and fr):
            return apology("You must enter at least texts for two languages", 400)

        if tm_ex == tm:
            return apology("The entry already exists", 400)
        if fr_ex == fr:
            return apology("The entry already exists", 400)
        if ru_ex == ru:
            return apology("The entry already exists", 400)

        db.execute("INSERT INTO dictionary (tm, fr, ru) VALUES (?,?,?)",
                   tm, fr,  ru)
        return render_template("input.html", tm=tm, ru=ru,  fr=fr)
    else:

        return render_template("input.html")


@app.route("/search")
def search():
    q = request.args.get("q")
    if q:
        dics = db.execute(
            "SELECT * FROM dictionary WHERE tm like ? or fr like ? or ru LIKE ? LIMIT 50", "%" + q + "%", "%" + q + "%", "%" + q + "%")
    else:
        dics = []
    return jsonify(dics)


@app.route('/upload', methods=["GET", "POST"])
def upload_file():
    if request.method == 'POST':
        lang = request.form.get("lang")

        if not lang:
            return apology("No language is selected", 400)
        # upload the file and save it to the current directory.
        file = request.files['file']
        if not file:
            return apology("No file is selected", 400)

        # we save word files with the same name so that we can delete them after execution.
        file.save("word.docx")

        word = docx2txt.process(file)  # Convert word to .txt file

        # Open a new text file and copy the converted text to it.
        textfile = open("text.txt", "w")
        textfile.write(word)
        textfile.close()

        tm_ex = db.execute("SELECT tm FROM prelim WHERE id=?", 1)
        fr_ex = db.execute("SELECT fr FROM prelim WHERE id=?", 1)
        ru_ex = db.execute("SELECT ru FROM prelim WHERE id=?", 1)

        # Reading lines of text and add them to the db.
        with open("text.txt", "r") as text:
            lines = text.readlines()
            if lang == "Turkmen":
                id = 1
                for line in lines:
                    if line[0].isalpha():
                        line.strip()
                        if tm_ex:

                            db.execute(
                                "UPDATE prelim SET tm=? WHERE id=?", line, id)
                            id += 1
                        else:
                            db.execute(
                                "INSERT INTO prelim (tm) VALUES (?)", line)
                    else:
                        continue
            elif lang == "French":
                id = 1
                for line in lines:
                    if line[0].isalpha():
                        line.strip()
                        if fr_ex:

                            db.execute(
                                "UPDATE prelim SET fr=? WHERE id=?", line, id)
                            id += 1
                        else:
                            db.execute(
                                "INSERT INTO prelim (fr) VALUES (?)", line)
                    else:
                        continue
            elif lang == "Russian":
                id = 1
                for line in lines:
                    if line[0].isalpha():
                        line.strip()
                        if ru_ex:
                            db.execute(
                                "UPDATE prelim SET ru=? WHERE id=?", line, id)
                            id += 1
                        else:
                            db.execute(
                                "INSERT INTO prelim (ru) VALUES (?)", line)
                    else:
                        continue
        
        os.remove("text.txt")  # remove both files after execution.
        os.remove("word.docx")
        prelim = db.execute("SELECT * FROM prelim")
        return render_template("upload.html", prelim=prelim)

    else:
        prelim = db.execute("SELECT * FROM prelim")
        return render_template('upload.html', prelim=prelim)


@app.route("/succes", methods=['POST'])
def succes():
    id = request.form.get("id")
    if id:
        db.execute(
            "INSERT INTO dictionary (tm, fr, ru) SELECT tm, fr, ru FROM prelim")
        db.execute(
            "DELETE FROM prelim")
        return render_template('succes.html')
    else:
        return apology("Please check your entry", 400)
