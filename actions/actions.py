from typing import Any, Text, Dict, List
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

API_KEY = "fd47f0604a-ad592f2962-tcqf4z"
API_URL = "https://api.fastforex.io/fetch-one"

MOEDAS_SUPORTADAS = {
    "USD": "Dolar Americano",
    "BRL": "Real Brasileiro",
    "EUR": "Euro",
    "GBP": "Libra Esterlina",
    "JPY": "Iene Japones",
    "ARS": "Peso Argentino",
    "CAD": "Dolar Canadense",
    "AUD": "Dolar Australiano",
    "CHF": "Franco Suico",
    "CNY": "Yuan Chines",
}

SINONIMOS = {
    "dolares": "USD", "dolar": "USD", "dollar": "USD", "dollars": "USD", "usd": "USD",
    "reais": "BRL", "real": "BRL", "brl": "BRL",
    "euros": "EUR", "euro": "EUR", "eur": "EUR",
    "libras": "GBP", "libra": "GBP", "gbp": "GBP",
    "ienes": "JPY", "iene": "JPY", "yen": "JPY", "jpy": "JPY",
    "pesos": "ARS", "peso": "ARS", "ars": "ARS",
}


def normalizar_moeda(texto):
    if not texto:
        return None
    texto = texto.strip().lower()
    return SINONIMOS.get(texto, texto.upper())


class ActionConverterMoeda(Action):
    def name(self) -> Text:
        return "action_converter_moeda"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent = tracker.latest_message.get("intent", {}).get("name")
        entities = tracker.latest_message.get("entities", [])
        texto = tracker.latest_message.get("text", "").strip()

        valor = tracker.get_slot("valor")
        moeda_origem = tracker.get_slot("moeda_origem")
        moeda_destino = tracker.get_slot("moeda_destino")
        pergunta = tracker.get_slot("pergunta_pendente")

        if intent == "converter_moeda":
            for ent in entities:
                if ent["entity"] == "valor":
                    valor = ent["value"]
                elif ent["entity"] == "moeda_origem":
                    moeda_origem = normalizar_moeda(ent["value"])
                elif ent["entity"] == "moeda_destino":
                    moeda_destino = normalizar_moeda(ent["value"])

        elif intent == "informar_valor":
            for ent in entities:
                if ent["entity"] == "valor":
                    valor = ent["value"]
                    break
            else:
                valor = texto

        elif intent == "informar_moeda":
            moeda = normalizar_moeda(texto)
            if pergunta == "moeda_destino":
                moeda_destino = moeda
            elif pergunta == "moeda_origem":
                moeda_origem = moeda
            elif not moeda_origem:
                moeda_origem = moeda
            else:
                moeda_destino = moeda

        if not valor:
            dispatcher.utter_message(text="Qual o valor que voce deseja converter?")
            return [
                SlotSet("valor", valor),
                SlotSet("moeda_origem", moeda_origem),
                SlotSet("moeda_destino", moeda_destino),
                SlotSet("pergunta_pendente", "valor"),
            ]

        if not moeda_origem:
            dispatcher.utter_message(text="Qual a moeda de origem? (ex: USD, BRL, EUR)")
            return [
                SlotSet("valor", valor),
                SlotSet("moeda_origem", moeda_origem),
                SlotSet("moeda_destino", moeda_destino),
                SlotSet("pergunta_pendente", "moeda_origem"),
            ]

        if not moeda_destino:
            dispatcher.utter_message(text="Qual a moeda de destino? (ex: USD, BRL, EUR)")
            return [
                SlotSet("valor", valor),
                SlotSet("moeda_origem", moeda_origem),
                SlotSet("moeda_destino", moeda_destino),
                SlotSet("pergunta_pendente", "moeda_destino"),
            ]

        try:
            valor_num = float(str(valor).replace(",", "."))
        except ValueError:
            dispatcher.utter_message(text="Nao consegui entender o valor. Informe um numero valido.")
            return [SlotSet("valor", None), SlotSet("pergunta_pendente", "valor")]

        try:
            response = requests.get(
                API_URL,
                params={"from": moeda_origem, "to": moeda_destino},
                headers={"X-API-Key": API_KEY},
            )
            data = response.json()

            if "error" in data:
                dispatcher.utter_message(text=f"Erro na API: {data['error']}")
                return [SlotSet("valor", None), SlotSet("moeda_origem", None), SlotSet("moeda_destino", None), SlotSet("pergunta_pendente", None)]

            taxa = data.get("result", {}).get(moeda_destino)
            if not taxa:
                dispatcher.utter_message(text=f"Nao encontrei a moeda {moeda_destino}. Verifique o codigo.")
                return [SlotSet("moeda_destino", None), SlotSet("pergunta_pendente", "moeda_destino")]

            resultado = valor_num * taxa
            dispatcher.utter_message(
                text=f"{valor_num:.2f} {moeda_origem} = {resultado:.2f} {moeda_destino} (taxa: {taxa:.4f})"
            )
        except Exception as e:
            dispatcher.utter_message(text=f"Erro ao consultar a API: {e}")

        return [SlotSet("valor", None), SlotSet("moeda_origem", None), SlotSet("moeda_destino", None), SlotSet("pergunta_pendente", None)]


class ActionListarMoedas(Action):
    def name(self) -> Text:
        return "action_listar_moedas"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        lista = "\n".join([f"- {codigo}: {nome}" for codigo, nome in MOEDAS_SUPORTADAS.items()])
        dispatcher.utter_message(text=f"Moedas suportadas:\n{lista}")
        return []
