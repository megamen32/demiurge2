from torch.cuda import OutOfMemoryError

model=None

def lazy_load_model():
    global device
    global feature_extractor
    global tokenizer
    global model


    from transformers import AutoTokenizer, ViTFeatureExtractor, VisionEncoderDecoderModel

    device = 'cuda'

    encoder_checkpoint = "nlpconnect/vit-gpt2-image-captioning"
    decoder_checkpoint = "nlpconnect/vit-gpt2-image-captioning"
    model_checkpoint = "nlpconnect/vit-gpt2-image-captioning"

    feature_extractor = ViTFeatureExtractor.from_pretrained(encoder_checkpoint)
    tokenizer = AutoTokenizer.from_pretrained(decoder_checkpoint)
    try:
        model = VisionEncoderDecoderModel.from_pretrained(model_checkpoint).to(device)
    except :
        device='cpu'
        model = VisionEncoderDecoderModel.from_pretrained(model_checkpoint).to('cpu')
def predict(image, max_length=64, num_beams=4):
    global model
    global device
    global feature_extractor
    global tokenizer
    global model
    if model is None:
        lazy_load_model()
    image = image.convert('RGB')
    image = feature_extractor(image, return_tensors="pt").pixel_values.to(device)
    clean_text = lambda x: x.replace('<|endoftext|>','').split('\n')[0]
    caption_ids = model.generate(image, max_length=max_length)[0]
    caption_text = clean_text(tokenizer.decode(caption_ids))
    return caption_text

if __name__=='__main__':
    from PIL import Image
    input = Image.open('image_0.png')
    examples = [f"image_{i}.png" for i in range(1, 7)]

    title = "Image Captioning "
    description = "Made by : shreyasdixit.tech"
    t=predict(image=input)
    print(t)