from load_xlsx_to_sqlite import load_reservations_to_sqlite, load_grouped_accounts_to_sqlite, delete_itzana_db
from dotenv import load_dotenv
from agents import Runner
from ItzanaAgents import reservations_agent

load_dotenv()

def load_db():

    # Borrando DB. 
    delete_itzana_db()

    reservations_loaded = load_reservations_to_sqlite("data/reservations.xlsx")
    accounts_loaded = load_grouped_accounts_to_sqlite("data/grouped_accounts.xlsx")

    print(f"Reservaciones cargadas a slqite: {reservations_loaded}")
    print(f"Grupos de cuentas cargadas a sqlite: {accounts_loaded}")

def main():

    #load_db()

    # Ejemplo de pregunta del usuario:
    pregunta = "Genera una tabla con la ocupacion por mes, para 2024. "
    pregunta = "Segun la inforamacion disponible, encuentra los tres meses con ocupacion mas baja. Excluye a partir de Marzo de 2025. "
    pregunta = input("> ")

    # Ejecutar el agente coordinador con la pregunta:
    resultado = Runner.run_sync(reservations_agent, pregunta)

    # Obtener la respuesta final estructurada:
    respuesta_final = resultado.final_output  # debería ser un objeto response_output
    print(respuesta_final)



if __name__ == "__main__":

    main()

