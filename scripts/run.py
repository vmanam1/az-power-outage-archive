providers = [
    APSProvider(),
    SRPProvider(),
]

for provider in providers:
    provider.run()