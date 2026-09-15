import numpy as np

# Simulate a professional dance
professional = np.random.rand(50, 99)

# User dance is similar but has small variations
user = professional + np.random.normal(0, 0.02, professional.shape)

np.save("sample_data/professional.npy", professional)
np.save("sample_data/user.npy", user)

print("Sample data created successfully!")
print("Professional shape:", professional.shape)
print("User shape:", user.shape)
