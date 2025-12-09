import cowsay
from transformers import pipeline

gen = pipeline("text2text-generation", model="facebook/blenderbot_small-90M")

cowsay.cow("Hello! Moo! Moo!")

while True:
    input_text = input("Chat, or type 'quit':")
    if input_text.lower() == "quit":
        cowsay.cow("Goodbye! Moo! Moo! Moo!")
        break


    # prompt the model to roleplay as a cow

    prompt = f"Pretend you are a cow. Answer the following questions: {input_text}"
    response = gen(prompt, max_length=200)
    response_text = response[0]["generated_text"] + "Moo!"

    # cowsay.cow(input_text + " Moo!")

    cowsay.cow(response_text)